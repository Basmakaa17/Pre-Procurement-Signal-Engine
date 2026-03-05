-- Procurement Taxonomy Seed Data
-- Maps grant themes to procurement categories with timing and confidence data

CREATE TABLE IF NOT EXISTS procurement_taxonomy (
    id serial PRIMARY KEY,
    grant_theme varchar(100) UNIQUE NOT NULL,
    procurement_category varchar(100) NOT NULL,
    lag_months_min integer NOT NULL,
    lag_months_max integer NOT NULL,
    confidence_base numeric(3,2),
    notes text
);

-- Insert seed data
INSERT INTO procurement_taxonomy (grant_theme, procurement_category, lag_months_min, lag_months_max, confidence_base, notes)
VALUES
    ('Cybersecurity Modernization', 'IT Security Consulting', 6, 9, 0.85, 'Municipal and provincial cyber programs consistently lead to security RFPs'),
    ('Digital Transformation', 'Software Development & IT Consulting', 3, 6, 0.90, 'Innovation pilots move to procurement fastest'),
    ('AI & Machine Learning', 'AI/ML Consulting & Development', 3, 8, 0.88, 'Federal AI strategy programs'),
    ('Healthcare Digitization', 'Health IT & EHR Systems', 6, 12, 0.82, 'Health Canada and provincial health authorities'),
    ('Clean Energy Infrastructure', 'Engineering & Construction', 12, 18, 0.75, 'Longer lead time due to project complexity'),
    ('Municipal Modernization', 'Cloud & SaaS Procurement', 6, 12, 0.80, 'Smart city and service digitization grants'),
    ('Workforce Development', 'Training & HR Consulting', 3, 9, 0.70, 'Skills programs often lead to workforce consulting RFPs'),
    ('Research & Innovation', 'Research & Advisory Services', 6, 12, 0.72, 'NRC and granting council programs'),
    ('Transportation & Logistics', 'Infrastructure & Systems Integration', 9, 18, 0.76, 'Transport Canada and provincial programs'),
    ('Environmental & Climate', 'Environmental Consulting', 6, 15, 0.74, 'Climate action funds and green programs'),
    ('Indigenous Programs', 'Community & Social Consulting', 6, 12, 0.68, 'ISC and Crown-Indigenous relations programs'),
    ('Defence & Security', 'Defence Consulting & Systems', 6, 12, 0.78, 'DND and public safety programs')
ON CONFLICT (grant_theme) DO NOTHING;
