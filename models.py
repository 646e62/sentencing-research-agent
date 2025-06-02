from sqlalchemy import Column, Integer, String, Date, Boolean, TIMESTAMP, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Sentence(Base):
    __tablename__ = 'sentences'

    id = Column(Integer, primary_key=True)
    case_id = Column(String, nullable=False)
    offender_name = Column(String, nullable=False)
    offence_code = Column(String, nullable=False)
    offence_date = Column(Date)
    sentence_imposed = Column(JSON)  # list of {penalty, quantum, quantum_type, mode}
    citation = Column(JSON)           # {offender_name, offence_code, offence_date, sentence, citation_paragraph, citation_text}
    is_appeal = Column(Boolean)
    dissent = Column(Boolean)
    lower_court_sentence_varied = Column(Boolean)
    higher_court_varied_sentence = Column(Boolean)
    time_analysis_started = Column(TIMESTAMP)
    time_analysis_stopped = Column(TIMESTAMP)
    human_verified = Column(Boolean)
    human_modified = Column(Boolean)
