from sqlalchemy import BigInteger, Column, ForeignKey, String, UniqueConstraint

from app.core.database import Base


class RoadmapStepSkillDB(Base):
    __tablename__ = "roadmap_step_skills"
    __table_args__ = (
        UniqueConstraint("roadmap_step_id", "skill_id", name="uq_step_skill"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    roadmap_step_id = Column(
        BigInteger, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(
        BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(50), nullable=False, server_default="quiz")
