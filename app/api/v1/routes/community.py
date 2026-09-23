from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, get_current_user_optional, require_role
from app.models.user import UserRole
from app.models.community import QuestionStatus
from app.schemas.auth import TokenPayload
from app.schemas.community import (
    CreatePostRequest,
    PostResponse,
    PostListResponse,
    CreateCommentRequest,
    CommentResponse,
    CreateFavoriteListRequest,
    AddToFavoriteListRequest,
    FavoriteListResponse,
    CreateGroupRequest,
    UpdateGroupRequest,
    GroupResponse,
    GroupDetailResponse,
    CreateQuestionRequest,
    QuestionResponse,
    CreateAnswerRequest,
    AnswerResponse,
    ReportContentRequest,
    StartLiveRequest,
    LiveSessionResponse,
    LiveTokenResponse,
)
from app.services import community_service, live_service

router = APIRouter(prefix="/community", tags=["Communauté"])


# --- Publications ---

@router.get("/posts", response_model=PostListResponse)
async def list_posts(
    author_id: Optional[str] = None,
    group_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Photos, vidéos, carnets de voyage, recommandations (§27). Filtrable par groupe via group_id.
    Sans group_id : fil public global visible par tous."""
    return await community_service.list_posts(
        author_id=author_id,
        group_id=group_id,
        page=page,
        page_size=page_size,
        current_user_id=current_user.sub if current_user else None,
    )


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: CreatePostRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Publier une photo, une vidéo ou un carnet de voyage."""
    return await community_service.create_post(data, author_id=current_user.sub)


@router.post("/posts/{post_id}/like", response_model=PostResponse)
async def like_post(post_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Aimer/retirer son like sur une publication (bascule selon l'état actuel)."""
    return await community_service.toggle_like_post(post_id, current_user.sub)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Supprimer sa publication (auteur/admin)."""
    await community_service.delete_post(post_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.get("/posts/{post_id}/comments", response_model=list)
async def list_comments(post_id: str):
    """Commentaires d'une publication."""
    return await community_service.list_comments(post_id)


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    post_id: str,
    data: CreateCommentRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Laisser un avis ou un commentaire."""
    return await community_service.add_comment(post_id, data, author_id=current_user.sub)


# --- Favoris ---

@router.get("/favorite-lists", response_model=list)
async def list_my_favorite_lists(current_user: TokenPayload = Depends(get_current_user)):
    """Ses listes de favoris / lieux à visiter."""
    return await community_service.list_my_favorite_lists(current_user.sub)


@router.post("/favorite-lists", response_model=FavoriteListResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite_list(
    data: CreateFavoriteListRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Créer une liste de favoris."""
    return await community_service.create_favorite_list(data, owner_id=current_user.sub)


@router.post("/favorite-lists/{list_id}/items", response_model=FavoriteListResponse)
async def add_to_favorite_list(
    list_id: str,
    data: AddToFavoriteListRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Ajouter un favori à une liste."""
    return await community_service.add_to_favorite_list(list_id, data.destination_id, current_user.sub)


@router.delete("/favorite-lists/{list_id}/items/{destination_id}", response_model=FavoriteListResponse)
async def remove_from_favorite_list(
    list_id: str,
    destination_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Retirer un favori d'une liste."""
    return await community_service.remove_from_favorite_list(list_id, destination_id, current_user.sub)


@router.delete("/favorite-lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite_list(
    list_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Supprimer une liste de favoris."""
    await community_service.delete_favorite_list(list_id, current_user.sub)


# --- Groupes de voyageurs ---

@router.get("/groups", response_model=list)
async def list_groups(
    public_only: bool = True,
    region: Optional[str] = None,
    province: Optional[str] = None,
    theme: Optional[str] = None,
):
    """Groupes de voyageurs, filtrables par région ou thème pour la découverte locale/internationale (§27)."""
    return await community_service.list_groups(public_only, region, theme, province)


@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: CreateGroupRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Créer un groupe de voyageurs."""
    return await community_service.create_group(data, creator_id=current_user.sub)


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group(group_id: str):
    """Détail d'un groupe : description et membres."""
    return await community_service.get_group_detail(group_id)


@router.patch("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    data: UpdateGroupRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Modifier les paramètres d'un groupe (nom, description, logo/photo de couverture,
    région, thème, visibilité) — réservé au créateur du groupe."""
    return await community_service.update_group(group_id, data, current_user.sub)


@router.post("/groups/{group_id}/join", response_model=GroupResponse)
async def join_group(group_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Rejoindre un groupe de voyageurs."""
    return await community_service.join_group(group_id, current_user.sub)


@router.post("/groups/{group_id}/leave", response_model=GroupResponse)
async def leave_group(group_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Quitter un groupe de voyageurs (sauf le créateur)."""
    return await community_service.leave_group(group_id, current_user.sub)


# --- Questions / réponses ---

@router.get("/questions", response_model=list)
async def list_questions(status_filter: Optional[QuestionStatus] = None):
    """Questions de la communauté."""
    return await community_service.list_questions(status_filter)


@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    data: CreateQuestionRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Poser une question."""
    return await community_service.create_question(data, author_id=current_user.sub)


@router.get("/questions/{question_id}/answers", response_model=list)
async def list_answers(question_id: str):
    """Réponses à une question."""
    return await community_service.list_answers(question_id)


@router.post("/questions/{question_id}/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def answer_question(
    question_id: str,
    data: CreateAnswerRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Répondre à une question."""
    return await community_service.answer_question(question_id, data, author_id=current_user.sub)


# --- Live streaming ---

@router.get("/live", response_model=list)
async def list_live_sessions(group_id: Optional[str] = None):
    """Lives en cours (globalement, ou filtrés sur un groupe)."""
    return await live_service.list_live_sessions(group_id)


@router.post("/live", response_model=LiveSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_live(
    data: StartLiveRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Démarrer un live : crée la session et la room LiveKit associée."""
    return await live_service.start_live(data, host_id=current_user.sub)


@router.get("/live/{session_id}", response_model=LiveSessionResponse)
async def get_live_session(session_id: str):
    """Détail d'une session de live."""
    return await live_service.get_live_session(session_id)


@router.post("/live/{session_id}/end", response_model=LiveSessionResponse)
async def end_live(session_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Terminer son propre live."""
    return await live_service.end_live(session_id, current_user.sub)


@router.post("/live/{session_id}/token", response_model=LiveTokenResponse)
async def get_live_token(session_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Jeton LiveKit pour rejoindre la room : publication vidéo pour l'hôte,
    lecture seule (+ chat texte) pour les spectateurs."""
    from app.services import user_service

    user = await user_service.get_user_by_id(current_user.sub)
    return await live_service.get_live_token(session_id, current_user.sub, user.full_name)


# --- Signalement ---

@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def report_content(
    data: ReportContentRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler un contenu trompeur."""
    return await community_service.report_content(data, reporter_id=current_user.sub)
