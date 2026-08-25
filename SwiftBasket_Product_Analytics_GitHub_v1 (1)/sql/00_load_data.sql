-- Run from the repository root with psql after executing 01_create_schema.sql.
-- psql -d swiftbasket -f sql/00_load_data.sql

\copy users FROM 'data/generated/users.csv' CSV HEADER;
\copy stores FROM 'data/generated/stores.csv' CSV HEADER;
\copy products FROM 'data/generated/products.csv' CSV HEADER;
\copy sessions FROM 'data/generated/sessions.csv' CSV HEADER;
\copy searches FROM 'data/generated/searches.csv' CSV HEADER;
\copy checkout_attempts FROM 'data/generated/checkout_attempts.csv' CSV HEADER NULL '';
\copy payment_attempts FROM 'data/generated/payment_attempts.csv' CSV HEADER NULL '';
\copy orders FROM 'data/generated/orders.csv' CSV HEADER NULL '';
\copy order_items FROM 'data/generated/order_items.csv' CSV HEADER;
\copy order_status_history FROM 'data/generated/order_status_history.csv' CSV HEADER NULL '';
\copy experiment_assignments FROM 'data/generated/experiment_assignments.csv' CSV HEADER NULL '';
\copy events FROM 'data/generated/events.csv' CSV HEADER NULL '';
