from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///site.db')
Session = sessionmaker(bind=engine)
session = Session()

def save_metadata_to_db(filename, metadata_info, user_id):
    # Add your save logic here
    pass

class Metadata(Base):
    __tablename__ = 'metadata'
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    metadata_info = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    # Add other fields as needed

# Create tables
Base.metadata.create_all(engine) 