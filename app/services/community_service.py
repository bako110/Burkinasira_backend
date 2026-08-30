from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.community import PostStatus, QuestionStatus, ContentReportStatus
from app.services import messaging_service
from app.schemas.community import (
    CreatePostRequest,
    PostResponse,
    CreateCommentRequest,
    CommentResponse,
    CreateFavoriteListRequest,
    FavoriteListResponse,
    CreateGroupRequest,
    GroupResponse,
    GroupDetailResponse,
    GroupMemberPublic,
    CreateQuestionRequest,
    QuestionResponse,
    CreateAnswerRequest,
    AnswerResponse,
    ReportContentRequest,
)

POSTS_COLLECTION = "community_posts"
COMMENTS_COLLECTION = "community_comments"
FAVORITES_COLLECTION = "favorite_lists"
GROUPS_COLLECTION = "traveler_groups"
QUESTIONS_COLLECTION = "community_questions"
ANSWERS_COLLECTION = "community_answers"
REPORTS_COLLECTION = "content_reports"
USERS_COLLECTION = "users"


# --- Publications ---

def _post_to_response(doc: dict, author_doc: Optional[dict] = None) -> PostResponse:
    return PostResponse(
        id=str(doc["_id"]),
        author_id=doc["author_id"],
        author_name=author_doc.get("full_name") if author_doc else None,
        author_avatar_url=author_doc.get("avatar_url") if author_doc else None,
        type=doc["type"],
        caption=doc.get("caption"),
        media_urls=doc.get("media_urls", []),
        related_destination_id=doc.get("related_destination_id"),
        group_id=doc.get("group_id"),
        location=doc.get("location"),
        like_count=doc.get("like_count", 0),
        comment_count=doc.get("comment_count", 0),
        created_at=doc["created_at"],
    )


async def create_post(data: CreatePostRequest, author_id: str) -> PostResponse:
    db = get_database()

    if data.group_id:
        if not ObjectId.is_valid(data.group_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
        group_doc = await db[GROUPS_COLLECTION].find_one({"_id": ObjectId(data.group_id)})
        if not group_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
        if author_id not in group_doc.get("member_ids", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les membres du groupe peuvent y publier",
            )

    now = datetime.utcnow()
    doc = data.model_dump()
    doc["author_id"] = author_id
    doc["like_count"] = 0
    doc["comment_count"] = 0
    doc["status"] = PostStatus.PUBLISHED.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[POSTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    author_doc = await db[USERS_COLLECTION].find_one({"_id": ObjectId(author_id)}) if ObjectId.is_valid(author_id) else None
    return _post_to_response(doc, author_doc)


async def list_posts(
    author_id: Optional[str] = None,
    group_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {"status": PostStatus.PUBLISHED.value}
    if author_id:
        query["author_id"] = author_id
    if group_id:
        query["group_id"] = group_id

    total = await db[POSTS_COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[POSTS_COLLECTION].find(query).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    author_ids = {d["author_id"] for d in docs if ObjectId.is_valid(d["author_id"])}
    author_docs = await db[USERS_COLLECTION].find({"_id": {"$in": [ObjectId(a) for a in author_ids]}}).to_list(length=None)
    authors_by_id = {str(a["_id"]): a for a in author_docs}

    items = [_post_to_response(d, authors_by_id.get(d["author_id"])) for d in docs]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def like_post(post_id: str) -> PostResponse:
    db = get_database()
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")
    result = await db[POSTS_COLLECTION].update_one({"_id": ObjectId(post_id)}, {"$inc": {"like_count": 1}})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")
    doc = await db[POSTS_COLLECTION].find_one({"_id": ObjectId(post_id)})
    return _post_to_response(doc)


async def delete_post(post_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")
    doc = await db[POSTS_COLLECTION].find_one({"_id": ObjectId(post_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")
    if doc["author_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres publications")
    await db[POSTS_COLLECTION].delete_one({"_id": ObjectId(post_id)})


# --- Commentaires ---

def _comment_to_response(doc: dict) -> CommentResponse:
    return CommentResponse(
        id=str(doc["_id"]),
        post_id=doc["post_id"],
        author_id=doc["author_id"],
        content=doc["content"],
        created_at=doc["created_at"],
    )


async def add_comment(post_id: str, data: CreateCommentRequest, author_id: str) -> CommentResponse:
    db = get_database()
    post = await db[POSTS_COLLECTION].find_one({"_id": ObjectId(post_id)}) if ObjectId.is_valid(post_id) else None
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")

    now = datetime.utcnow()
    doc = {"post_id": post_id, "author_id": author_id, "content": data.content, "created_at": now}
    result = await db[COMMENTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await db[POSTS_COLLECTION].update_one({"_id": ObjectId(post_id)}, {"$inc": {"comment_count": 1}})
    return _comment_to_response(doc)


async def list_comments(post_id: str) -> list:
    db = get_database()
    docs = await db[COMMENTS_COLLECTION].find({"post_id": post_id}).sort("created_at", 1).to_list(length=None)
    return [_comment_to_response(d) for d in docs]


# --- Favoris ---

def _favorite_list_to_response(doc: dict) -> FavoriteListResponse:
    return FavoriteListResponse(
        id=str(doc["_id"]),
        owner_id=doc["owner_id"],
        name=doc["name"],
        destination_ids=doc.get("destination_ids", []),
        created_at=doc["created_at"],
    )


async def create_favorite_list(data: CreateFavoriteListRequest, owner_id: str) -> FavoriteListResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = {"owner_id": owner_id, "name": data.name, "destination_ids": [], "created_at": now, "updated_at": now}
    result = await db[FAVORITES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _favorite_list_to_response(doc)


async def list_my_favorite_lists(owner_id: str) -> list:
    db = get_database()
    docs = await db[FAVORITES_COLLECTION].find({"owner_id": owner_id}).to_list(length=None)
    return [_favorite_list_to_response(d) for d in docs]


async def add_to_favorite_list(list_id: str, destination_id: str, owner_id: str) -> FavoriteListResponse:
    db = get_database()
    if not ObjectId.is_valid(list_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    doc = await db[FAVORITES_COLLECTION].find_one({"_id": ObjectId(list_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    if doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres listes")

    await db[FAVORITES_COLLECTION].update_one(
        {"_id": ObjectId(list_id)},
        {"$addToSet": {"destination_ids": destination_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    doc = await db[FAVORITES_COLLECTION].find_one({"_id": ObjectId(list_id)})
    return _favorite_list_to_response(doc)


async def remove_from_favorite_list(list_id: str, destination_id: str, owner_id: str) -> FavoriteListResponse:
    db = get_database()
    if not ObjectId.is_valid(list_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    doc = await db[FAVORITES_COLLECTION].find_one({"_id": ObjectId(list_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    if doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres listes")

    await db[FAVORITES_COLLECTION].update_one(
        {"_id": ObjectId(list_id)},
        {"$pull": {"destination_ids": destination_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    doc = await db[FAVORITES_COLLECTION].find_one({"_id": ObjectId(list_id)})
    return _favorite_list_to_response(doc)


async def delete_favorite_list(list_id: str, owner_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(list_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    doc = await db[FAVORITES_COLLECTION].find_one({"_id": ObjectId(list_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liste introuvable")
    if doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres listes")
    await db[FAVORITES_COLLECTION].delete_one({"_id": ObjectId(list_id)})


# --- Groupes de voyageurs ---

def _group_to_response(doc: dict) -> GroupResponse:
    return GroupResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description"),
        cover_photo=doc.get("cover_photo"),
        region=doc.get("region"),
        province=doc.get("province"),
        theme=doc.get("theme"),
        creator_id=doc["creator_id"],
        member_ids=doc.get("member_ids", []),
        conversation_id=doc.get("conversation_id"),
        is_public=doc.get("is_public", True),
        created_at=doc["created_at"],
    )


async def create_group(data: CreateGroupRequest, creator_id: str) -> GroupResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["creator_id"] = creator_id
    doc["member_ids"] = [creator_id]
    doc["conversation_id"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[GROUPS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    conversation_id = await messaging_service.create_group_conversation(str(doc["_id"]), creator_id)
    await db[GROUPS_COLLECTION].update_one(
        {"_id": doc["_id"]}, {"$set": {"conversation_id": conversation_id}}
    )
    doc["conversation_id"] = conversation_id

    return _group_to_response(doc)


async def list_groups(
    public_only: bool = True,
    region: Optional[str] = None,
    theme: Optional[str] = None,
    province: Optional[str] = None,
) -> list:
    db = get_database()
    query: dict = {"is_public": True} if public_only else {}
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if theme:
        query["theme"] = theme
    docs = await db[GROUPS_COLLECTION].find(query).to_list(length=None)
    return [_group_to_response(d) for d in docs]


async def join_group(group_id: str, user_id: str) -> GroupResponse:
    db = get_database()
    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    result = await db[GROUPS_COLLECTION].update_one(
        {"_id": ObjectId(group_id)},
        {"$addToSet": {"member_ids": user_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    doc = await db[GROUPS_COLLECTION].find_one({"_id": ObjectId(group_id)})
    if doc.get("conversation_id"):
        await messaging_service.add_group_conversation_participant(doc["conversation_id"], user_id)
    return _group_to_response(doc)


async def leave_group(group_id: str, user_id: str) -> GroupResponse:
    db = get_database()
    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    doc = await db[GROUPS_COLLECTION].find_one({"_id": ObjectId(group_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    if doc.get("creator_id") == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le créateur ne peut pas quitter son propre groupe",
        )
    await db[GROUPS_COLLECTION].update_one(
        {"_id": ObjectId(group_id)},
        {"$pull": {"member_ids": user_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    doc = await db[GROUPS_COLLECTION].find_one({"_id": ObjectId(group_id)})
    if doc.get("conversation_id"):
        await messaging_service.remove_group_conversation_participant(doc["conversation_id"], user_id)
    return _group_to_response(doc)


async def get_group_detail(group_id: str) -> GroupDetailResponse:
    db = get_database()
    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")
    doc = await db[GROUPS_COLLECTION].find_one({"_id": ObjectId(group_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable")

    member_ids = doc.get("member_ids", [])
    object_ids = [ObjectId(uid) for uid in member_ids if ObjectId.is_valid(uid)]
    user_docs = await db[USERS_COLLECTION].find({"_id": {"$in": object_ids}}).to_list(length=None)
    users_by_id = {str(u["_id"]): u for u in user_docs}

    members = [
        GroupMemberPublic(
            id=uid,
            full_name=users_by_id[uid]["full_name"] if uid in users_by_id else "Utilisateur GoTours",
            avatar_url=users_by_id[uid].get("avatar_url") if uid in users_by_id else None,
        )
        for uid in member_ids
    ]

    return GroupDetailResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description"),
        cover_photo=doc.get("cover_photo"),
        region=doc.get("region"),
        province=doc.get("province"),
        theme=doc.get("theme"),
        creator_id=doc["creator_id"],
        members=members,
        conversation_id=doc.get("conversation_id"),
        is_public=doc.get("is_public", True),
        created_at=doc["created_at"],
    )


# --- Questions / réponses ---

def _question_to_response(doc: dict) -> QuestionResponse:
    return QuestionResponse(
        id=str(doc["_id"]),
        author_id=doc["author_id"],
        title=doc["title"],
        content=doc["content"],
        related_destination_id=doc.get("related_destination_id"),
        status=doc.get("status", QuestionStatus.OPEN.value),
        created_at=doc["created_at"],
    )


async def create_question(data: CreateQuestionRequest, author_id: str) -> QuestionResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["author_id"] = author_id
    doc["status"] = QuestionStatus.OPEN.value
    doc["created_at"] = now
    result = await db[QUESTIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _question_to_response(doc)


async def list_questions(status_filter: Optional[QuestionStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, QuestionStatus) else status_filter
    docs = await db[QUESTIONS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_question_to_response(d) for d in docs]


def _answer_to_response(doc: dict) -> AnswerResponse:
    return AnswerResponse(
        id=str(doc["_id"]),
        question_id=doc["question_id"],
        author_id=doc["author_id"],
        content=doc["content"],
        created_at=doc["created_at"],
    )


async def answer_question(question_id: str, data: CreateAnswerRequest, author_id: str) -> AnswerResponse:
    db = get_database()
    if not ObjectId.is_valid(question_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")
    question = await db[QUESTIONS_COLLECTION].find_one({"_id": ObjectId(question_id)})
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")

    now = datetime.utcnow()
    doc = {"question_id": question_id, "author_id": author_id, "content": data.content, "created_at": now}
    result = await db[ANSWERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await db[QUESTIONS_COLLECTION].update_one({"_id": ObjectId(question_id)}, {"$set": {"status": QuestionStatus.ANSWERED.value}})
    return _answer_to_response(doc)


async def list_answers(question_id: str) -> list:
    db = get_database()
    docs = await db[ANSWERS_COLLECTION].find({"question_id": question_id}).sort("created_at", 1).to_list(length=None)
    return [_answer_to_response(d) for d in docs]


# --- Signalement de contenu ---

async def report_content(data: ReportContentRequest, reporter_id: str) -> dict:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["status"] = ContentReportStatus.REPORTED.value
    doc["moderated_by"] = None
    doc["created_at"] = now
    result = await db[REPORTS_COLLECTION].insert_one(doc)
    return {"id": str(result.inserted_id), "status": "reported"}
