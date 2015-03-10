-- This file should be placed in the same directory as the sqlite database file that is to contain this table.

CREATE TABLE JobPostings (
    Id TEXT NOT NULL UNIQUE, 
    Company TEXT, 
    Title TEXT NOT NULL, 
    Locale TEXT, 
    URL TEXT NOT NULL, 
    postedDate DATETIME, 
    insertedDate DATETIME DEFAULT ((datetime('now', 'localtime')))
);