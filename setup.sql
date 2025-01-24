-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create form_responses table
CREATE TABLE IF NOT EXISTS form_responses (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    form_id bigint NOT NULL,
    response_data jsonb NOT NULL,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT fk_form
        FOREIGN KEY (form_id)
        REFERENCES forms(id)
        ON DELETE CASCADE
);

-- Grant permissions
GRANT ALL ON form_responses TO authenticated;
GRANT ALL ON form_responses TO service_role;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_form_responses_form_id ON form_responses(form_id); 