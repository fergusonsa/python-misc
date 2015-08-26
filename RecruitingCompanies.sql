-- This file should be placed in the same directory as the sqlite database file that is to contain this table.

CREATE TABLE RecruitingCompanies (
    Name TEXT PRIMARY KEY UNIQUE,
    DateContacted DATETIME,
    Comment TEXT,
    ResumeSubmitted BOOLEAN DEFAULT (0),
    NotInterested BOOLEAN DEFAULT (0),
    URL TEXT,
    CannotSubmitResume BOOLEAN DEFAULT (0),
    DateInserted DATETIME,
    Telephone TEXT DEFAULT (''),
    ContactPerson TEXT DEFAULT (''),
    NearestOffice TEXT DEFAULT (''));
