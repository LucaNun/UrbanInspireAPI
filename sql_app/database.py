from sqlmodel import create_engine, SQLModel, Session, select
import secret
from sql_app.models import User_Group, Idea_Status

DATABASE_URL = f"postgresql://{secret.DB_USER}:{secret.DB_PASSWORD}@{secret.DB_IP}/UrbanInspire"

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    insert_data()

def insert_data():
    with Session(engine) as session:
        statement = select(User_Group)
        result = session.exec(statement).first()
        
        if not result:
            admin = User_Group(name="Admin")
            user = User_Group(name="User")

            session.add(admin)
            session.add(user)

            # Änderungen speichern
            session.commit()
            
        statement = select(Idea_Status)
        result = session.exec(statement).first()
        
        if not result:
            new = Idea_Status(name="new")
            done = Idea_Status(name="done")
            waiting_votes = Idea_Status(name="waiting votes")
            failed = Idea_Status(name="failed")
            hidden = Idea_Status(name="hidden")

            session.add(new)
            session.add(done)
            session.add(waiting_votes)
            session.add(failed)
            session.add(hidden)

            # Änderungen speichern
            session.commit()

def get_db_session():
    with Session(engine) as session:
        yield session
