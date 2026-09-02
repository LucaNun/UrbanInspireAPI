from sqlmodel import create_engine, SQLModel, Session, select, delete
import secret
from sql_app.models import User_Group, Idea_Status, Idea_Categories, User_Token, User, ResetPassword
from datetime import datetime, timedelta

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
            new = Idea_Status(name="Neu")
            done = Idea_Status(name="Fertig")
            waiting_votes = Idea_Status(name="In Abstimmung")
            failed = Idea_Status(name="Fehlgeschlagen")
            hidden = Idea_Status(name="Versteckt")
            reported = Idea_Status(name="Gemeldet")

            session.add(new)
            session.add(done)
            session.add(waiting_votes)
            session.add(failed)
            session.add(hidden)
            session.add(reported)

            # Änderungen speichern
            session.commit()
        
        statement = select(Idea_Categories)
        result = session.exec(statement).first()
        
        if not result:
            default = Idea_Categories(name="nicht zugewiesen")
            gebaude = Idea_Categories(name="Gebäude")
            vaeranstaltung = Idea_Categories(name="Veranstaltung")
            festival = Idea_Categories(name="Festival")
            restaurant = Idea_Categories(name="Restaurant")
            sonstige = Idea_Categories(name="Sonstige")
            
            session.add(default)
            session.add(gebaude)
            session.add(vaeranstaltung)
            session.add(festival)
            session.add(restaurant)
            session.add(sonstige)

            # Änderungen speichern
            session.commit()
        
        
def get_db_session():
    with Session(engine) as session:
        yield session

def cleanup_tokens():
    print("Running cleanup_tokens job...")
    with Session(engine) as session:
        statement = delete(User_Token).where(
            User_Token.exp < int(datetime.now().timestamp())
        )
        result = session.exec(statement)
        session.commit()
        print(f"Deleted {result.rowcount} expired tokens")
    print("Finished cleanup_tokens job")

def cleanup_unactiveded_users():
    print("Running cleanup_unactive_users job...")
    with Session(engine) as session:
        statement = delete(User).where(
            User.modify_date < datetime.now() - timedelta(days=30),
            User.is_active == False
        )
        result = session.exec(statement)
        session.commit()
        print(f"Deleted {result.rowcount} expired acounts")
    print("Finished cleanup_unactive_users job")
    
def cleanup_unused_password_reset_tokens():
    print("Running cleanup_unused_password_reset_tokens job...")
    with Session(engine) as session:
        statement = delete(ResetPassword).where(
            ResetPassword.ttl < datetime.now()
        )
        result = session.exec(statement)
        session.commit()
        print(f"Deleted {result.rowcount} expired password reset tokens")
    print("Finished cleanup_unused_password_reset_tokens job")
