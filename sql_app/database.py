from sqlmodel import create_engine, SQLModel, Session
import secret

DATABASE_URL = f"postgresql://{secret.DB_USER}:{secret.DB_PASSWORD}@{secret.DB_IP}/UrbanInspire"

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
