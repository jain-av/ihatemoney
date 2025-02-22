from ihatemoney.run import create_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

application = create_app()

# Example of creating an engine and session using SQLAlchemy 2.0 style.
# Replace with your actual database URL.
engine = create_engine("sqlite:///:memory:", future=True)

# Create a session factory
Session = sessionmaker(bind=engine, future=True)

# Use the session
# Example:
# with Session() as session:
#     # Your database operations here
#     pass
