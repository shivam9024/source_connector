from fastapi import FastAPI, status, HTTPException, Depends , File, UploadFile
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Organization, Workspace, Source,File as FileModel

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

class OurBaseModel(BaseModel):
    class Config:
        orm_mode = True

class WorkspaceCreate(OurBaseModel):
    name: str
    description: str = None
    is_active: bool = False
    processed_chunks: int = 0

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WorkspaceResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    is_active: bool
    description: Optional[str]
    processed_chunks: int
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]

    class Config:
        anystr_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @staticmethod
    def from_orm(workspace):
        return WorkspaceResponse(
            id=workspace.id,
            organization_id=workspace.organization_id,
            name=workspace.name,
            is_active=workspace.is_active,
            description=workspace.description,
            processed_chunks=workspace.processed_chunks,
            created_at=workspace.created_at.isoformat() if workspace.created_at else None,
            updated_at=workspace.updated_at.isoformat() if workspace.updated_at else None,
            deleted_at=workspace.deleted_at.isoformat() if workspace.deleted_at else None
        )
    
class OrganizationResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] 
    description: Optional[str] 
    created_at: Optional[str] 
    updated_at: Optional[str] 
    deleted_at: Optional[str]

    class Config:
        anystr_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @staticmethod
    def from_orm(organization):
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            domain=organization.domain,
            description=organization.description,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
            updated_at=organization.updated_at.isoformat() if organization.updated_at else None,
            deleted_at=organization.deleted_at.isoformat() if organization.deleted_at else None
        )
    
class SourceCreate(BaseModel):
    source_type: str

class SourceResponse(BaseModel):
    id: int
    workspace_id: int
    source_type: str
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]

    class Config:
        anystr_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @staticmethod
    def from_orm(source):
        return SourceResponse(
            id=source.id,
            workspace_id=source.workspace_id,
            source_type=source.source_type,
            created_at=source.created_at.isoformat() if source.created_at else None,
            updated_at=source.updated_at.isoformat() if source.updated_at else None,
            deleted_at=source.deleted_at.isoformat() if source.deleted_at else None
        )

    
# Define a Pydantic model for file response
class FileResponse(BaseModel):
    id: int
    workspace_id: int
    filename: str
    mimetype: str
    size: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]

    class Config:
        anystr_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/api/v1/organization/{organization_id}/workspace', response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def add_workspace(organization_id: int, workspace: WorkspaceCreate, db: Session = Depends(get_db)):
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")


    new_workspace = Workspace(
        organization_id=organization_id,
        name=workspace.name,
        description=workspace.description,
        is_active=workspace.is_active,
        processed_chunks=workspace.processed_chunks
    )
    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)
     # Convert datetime fields to string
    new_workspace_dict = new_workspace.__dict__
    new_workspace_dict['created_at'] = new_workspace_dict['created_at'].isoformat()
    new_workspace_dict['updated_at'] = new_workspace_dict['updated_at'].isoformat()

    return new_workspace_dict


@app.get('/api/v1/organization/{organization_id}/workspace/{workspace_id}', response_model=WorkspaceResponse, status_code=status.HTTP_200_OK)
def get_workspace_by_id(organization_id: int, workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.organization_id == organization_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Convert datetime to string
    workspace_dict = workspace.__dict__
    workspace_dict['created_at'] = workspace_dict['created_at'].isoformat()  # or any other string format
    workspace_dict['updated_at'] = workspace_dict['updated_at'].isoformat()

    return workspace_dict



@app.delete('/api/v1/organization/{organization_id}/workspace/{workspace_id}', response_model=WorkspaceResponse, status_code=status.HTTP_200_OK)
def delete_workspace(organization_id: int, workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.organization_id == organization_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace.deleted_at = datetime.now()
    response_data = WorkspaceResponse.from_orm(workspace)
    db.delete(workspace)
    db.commit()
    return response_data

# @app.post('/api/v1/workspace/{workspace_id}/file_upload', status_code=status.HTTP_200_OK)
# def upload_file(workspace_id: int):
#     return {"message": "File uploaded successfully", "workspace_id": workspace_id}
@app.post('/api/v1/workspace/{workspace_id}/file_upload', response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(workspace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Check if workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Read file details
    file_content = await file.read()
    file_size = len(file_content)
    file_mimetype = file.content_type

    # Create a new File record
    new_file = FileModel(
        workspace_id=workspace_id,
        filename=file.filename,
        mimetype=file_mimetype,
        size=file_size
    )
    
    # Add and commit to the database
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # Return the file details
    return FileResponse(
        id=new_file.id,
        workspace_id=new_file.workspace_id,
        filename=new_file.filename,
        mimetype=new_file.mimetype,
        size=new_file.size,
        created_at=new_file.created_at.isoformat() if new_file.created_at else None,
        updated_at=new_file.updated_at.isoformat() if new_file.updated_at else None,
        deleted_at=new_file.deleted_at.isoformat() if new_file.deleted_at else None
    )


@app.post('/api/v1/workspace/{workspace_id}/source', response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def add_source(workspace_id: int, source: SourceCreate, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    new_source = Source(
        workspace_id=workspace_id,
        source_type=source.source_type
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return SourceResponse.from_orm(new_source)

@app.get('/api/v1/workspace/{workspace_id}/source/{source_id}', response_model=SourceResponse, status_code=status.HTTP_200_OK)
def get_source_by_id(workspace_id: int, source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id, Source.workspace_id == workspace_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.from_orm(source)

@app.put('/api/v1/workspace/{workspace_id}/source/{source_id}', response_model=SourceResponse, status_code=status.HTTP_200_OK)
def update_source(workspace_id: int, source_id: int, source: SourceCreate, db: Session = Depends(get_db)):
    source_db = db.query(Source).filter(Source.id == source_id, Source.workspace_id == workspace_id).first()
    if not source_db:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source_db.source_type = source.source_type
    source_db.updated_at = datetime.now()
    db.commit()
    db.refresh(source_db)
    
    # Create a SourceResponse from source_db instead of source
    return SourceResponse.from_orm(source_db)


@app.get('/test')
def test_route():
    return {"message": "Test route is working"}

