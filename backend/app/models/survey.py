from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    SmallInteger,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base
from app.models.enums import survey_question_type_enum


class SurveyQuestionDB(Base):
    __tablename__ = "survey_questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    prompt = Column(String(500), nullable=False)
    question_type = Column(survey_question_type_enum, nullable=False)
    options = Column(JSON, nullable=True)
    maps_to_profile_field = Column(String(50), nullable=True)
    priority = Column(SmallInteger, default=0, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
