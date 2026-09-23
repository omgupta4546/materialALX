import uuid
from sqlalchemy.orm import Session
from app.core.connection import engine, SessionLocal
from app.models.base import Classification
from app.repositories.base import ClassificationRepo

def seed_classifications(db: Session):
    repo = ClassificationRepo(db)
    
    # 1. Mechanical
    mech_id = str(uuid.uuid4())
    repo.create(
        classification_id=mech_id,
        code="MECH",
        name="Mechanical",
        level=0,
        description="Mechanical equipment and components"
    )
    
    # Mechanical -> Bearings
    brg_id = str(uuid.uuid4())
    repo.create(
        classification_id=brg_id,
        parent_id=mech_id,
        code="MECH-BRG",
        name="Bearings",
        level=1
    )
    
    # Mechanical -> Bearings -> Deep Groove Ball Bearings
    repo.create(
        classification_id=str(uuid.uuid4()),
        parent_id=brg_id,
        code="MECH-BRG-DGBB",
        name="Deep Groove Ball Bearings",
        level=2
    )

    # Mechanical -> Valves
    vlv_id = str(uuid.uuid4())
    repo.create(
        classification_id=vlv_id,
        parent_id=mech_id,
        code="MECH-VLV",
        name="Valves",
        level=1
    )

    # Mechanical -> Valves -> Gate Valves
    repo.create(
        classification_id=str(uuid.uuid4()),
        parent_id=vlv_id,
        code="MECH-VLV-GATE",
        name="Gate Valves",
        level=2
    )

    # 2. Electrical
    elec_id = str(uuid.uuid4())
    repo.create(
        classification_id=elec_id,
        code="ELEC",
        name="Electrical",
        level=0
    )

    # Electrical -> Motors
    mot_id = str(uuid.uuid4())
    repo.create(
        classification_id=mot_id,
        parent_id=elec_id,
        code="ELEC-MOT",
        name="Motors",
        level=1
    )
    
    # Electrical -> Motors -> AC Motors
    repo.create(
        classification_id=str(uuid.uuid4()),
        parent_id=mot_id,
        code="ELEC-MOT-AC",
        name="AC Motors",
        level=2
    )
    
    print("Classifications seeded successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Classification).count() == 0:
            seed_classifications(db)
            db.commit()
        else:
            print("Classifications already seeded.")
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()
