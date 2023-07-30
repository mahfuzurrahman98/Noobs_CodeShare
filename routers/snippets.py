from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from utils import UID

from database import db
from models.Snippet import Snippet
from schemas.SnippetSchema import createSnippetSchema, updateSnippetSchema, privateSnippetSchema
from validators.snippetValidator import (validate_delete_snippet,
                                         validate_new_snippet,
                                         validate_update_snippet)

router = APIRouter()


# create a snippet
@router.post('/snippets')
def store(request: Request, snippet: Annotated[createSnippetSchema, Depends(validate_new_snippet)]):

    try:
        new_snippet = Snippet(
            uid=UID.generate(),
            title=snippet.title,
            source_code=snippet.source_code,
            language=snippet.language,
            tags=','.join(snippet.tags)
            if (snippet.tags and len(snippet.tags) > 0)
            else None,
            visibility=snippet.visibility,
            pass_code=snippet.pass_code if snippet.pass_code is not None else None,
            theme=snippet.theme if snippet.theme is not None else 'monokai',
            font_size=snippet.font_size if snippet.font_size is not None else 14,
            user_id=request.state.user.get('id')
        )
        db.add(new_snippet)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'detail': 'Snippet create successfully',
                'data': {
                    snippet: new_snippet.serialize()
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# get only your snippets
@router.get('/snippets')
def index(request: Request):
    try:
        snippets = db.query(Snippet).filter(
            Snippet.user_id == request.state.user.get('id')
        ).all()

        if len(snippets) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    'detail': 'You have no snippets yet',
                }
            )

        snippets = [snippet.serialize() for snippet in snippets]
        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Snipppets fetched successfully',
                'data': {
                    'snippets': snippets
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# get all public snippets
@router.get('/snippets/public')
def get_public_snippets(request: Request):
    try:
        snippets = db.query(Snippet).filter(
            Snippet.visibility == 1
        ).all()

        if len(snippets) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    'detail': 'No snippets found',
                }
            )

        snippets = [snippet.serialize() for snippet in snippets]
        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Snipppets fetched successfully',
                'data': {
                    'snippets': snippets
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# get a single snippet
@router.get('/snippets/{uid}')
def show(request: Request, uid: str):
    try:
        snippet = db.query(Snippet).filter(
            Snippet.uid == uid
        ).first()

        if snippet is None:
            return JSONResponse(
                status_code=404,
                content={
                    'detail': 'Snippets not found',
                }
            )

        if (snippet.user_id != request.state.user.get('id') and snippet.visibility == 2):
            raise HTTPException(
                status_code=403, detail='Access denied, this snippet is private')

        snippet = snippet.serialize()
        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Snipppet fetched successfully',
                'data': {
                    'snippet': snippet
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# get a private snippet with passcode
@router.post('/snippets/private/{uid}')
def show(request: Request, uid: str, pass_code: privateSnippetSchema):
    try:
        snippet = db.query(Snippet).filter(
            Snippet.uid == uid
        ).first()

        if snippet is None:
            return JSONResponse(
                status_code=404,
                content={
                    'detail': 'Snippets not found',
                }
            )

        if (snippet.pass_code != pass_code):
            raise HTTPException(
                status_code=403,
                detail='Access denied, provide the correct passcode'
            )

        snippet = snippet.serialize()
        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Snipppet fetched successfully',
                'data': {
                    'snippet': snippet
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------


@router.put('/snippets/{id}')
def update(request: Request, id: int, snippet: Annotated[updateSnippetSchema, Depends(validate_update_snippet)]):
    # Find the snippet to update
    _snippet = db.query(Snippet).filter(Snippet.id == id).first()
    if not _snippet:
        raise HTTPException(status_code=404, detail='Snippet not found')

    # Update the snippet attributes based on the request
    _snippet.title = snippet.title if snippet.title is not None else _snippet.title
    _snippet.content = snippet.content if snippet.content is not None else _snippet.content
    _snippet.language = snippet.language if snippet.language is not None else _snippet.language
    _snippet.visibility = snippet.visibility if snippet.visibility is not None else _snippet.visibility
    _snippet.share_with = snippet.share_with if snippet.visibility == 2 else None

    try:
        db.commit()
        return {
            'detail': 'Snippet updated successfully',
            'data': {
                'snippet': {
                    'id': _snippet.id,
                    'uid': _snippet.uid,
                    'title': _snippet.title,
                    'content': _snippet.content,
                    'visibility': _snippet.visibility,
                    'language': _snippet.programming_language.name,
                }
            }
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/snippets/{id}')
def destroy(request: Request, snippet: Snippet = Depends(validate_delete_snippet)):
    try:
        db.delete(snippet)
        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                'detail': 'Snippet deleted successfully',
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
