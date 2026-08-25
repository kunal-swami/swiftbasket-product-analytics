-- SwiftBasket synthetic product-analytics schema (PostgreSQL)
-- All timestamps are stored in UTC. All records are simulated.

CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL,
    signup_completed_at TIMESTAMPTZ,
    acquisition_channel VARCHAR(30) NOT NULL,
    campaign_name VARCHAR(100),
    initial_city VARCHAR(50) NOT NULL,
    initial_platform VARCHAR(20) NOT NULL CHECK (initial_platform IN ('Android','iOS')),
    device_tier VARCHAR(20) CHECK (device_tier IN ('low','mid','high')),
    is_serviceable BOOLEAN NOT NULL,
    acquisition_cost NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (acquisition_cost >= 0),
    CHECK (signup_completed_at IS NULL OR signup_completed_at >= first_seen_at)
);

CREATE TABLE stores (
    store_id BIGINT PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL UNIQUE,
    city VARCHAR(50) NOT NULL,
    zone VARCHAR(50) NOT NULL,
    opened_at DATE NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    mrp NUMERIC(10,2) NOT NULL CHECK (mrp > 0),
    base_selling_price NUMERIC(10,2) NOT NULL CHECK (base_selling_price > 0),
    is_active BOOLEAN NOT NULL,
    CHECK (base_selling_price <= mrp)
);

CREATE TABLE sessions (
    session_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    session_started_at TIMESTAMPTZ NOT NULL,
    session_ended_at TIMESTAMPTZ NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('Android','iOS')),
    app_version VARCHAR(20) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    network_type VARCHAR(20) CHECK (network_type IN ('Wi-Fi','4G','5G')),
    city VARCHAR(50) NOT NULL,
    store_id BIGINT REFERENCES stores(store_id),
    CHECK (session_ended_at >= session_started_at),
    UNIQUE (session_id, user_id)
);

CREATE TABLE searches (
    search_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    searched_at TIMESTAMPTZ NOT NULL,
    search_query VARCHAR(200) NOT NULL,
    result_count INTEGER NOT NULL CHECK (result_count >= 0),
    response_time_ms INTEGER NOT NULL CHECK (response_time_ms >= 0),
    FOREIGN KEY (session_id, user_id) REFERENCES sessions(session_id, user_id)
);

CREATE TABLE checkout_attempts (
    checkout_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL REFERENCES stores(store_id),
    checkout_started_at TIMESTAMPTZ NOT NULL,
    checkout_ended_at TIMESTAMPTZ NOT NULL,
    item_count INTEGER NOT NULL CHECK (item_count > 0),
    subtotal NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    delivery_fee NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (delivery_fee >= 0),
    handling_fee NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (handling_fee >= 0),
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    total_payable NUMERIC(12,2) NOT NULL CHECK (total_payable >= 0),
    estimated_delivery_minutes INTEGER NOT NULL CHECK (estimated_delivery_minutes > 0),
    checkout_outcome VARCHAR(30) NOT NULL CHECK (checkout_outcome IN ('abandoned','payment_failed','order_created')),
    abandonment_stage VARCHAR(50),
    FOREIGN KEY (session_id, user_id) REFERENCES sessions(session_id, user_id),
    UNIQUE (checkout_id, user_id, store_id),
    CHECK (checkout_ended_at >= checkout_started_at),
    CHECK (ABS(total_payable - (subtotal + delivery_fee + handling_fee - discount_amount)) <= 0.01)
);

CREATE TABLE payment_attempts (
    payment_attempt_id BIGINT PRIMARY KEY,
    checkout_id BIGINT NOT NULL REFERENCES checkout_attempts(checkout_id),
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    attempted_at TIMESTAMPTZ NOT NULL,
    payment_method VARCHAR(30) NOT NULL CHECK (payment_method IN ('UPI','card','wallet','netbanking')),
    payment_provider VARCHAR(50),
    payment_status VARCHAR(20) NOT NULL CHECK (payment_status IN ('success','failed','pending')),
    failure_code VARCHAR(50),
    failure_reason VARCHAR(150),
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
    UNIQUE (checkout_id, attempt_number)
);

CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    checkout_id BIGINT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    order_placed_at TIMESTAMPTZ NOT NULL,
    confirmed_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    final_status VARCHAR(30) NOT NULL CHECK (final_status IN ('delivered','cancelled_by_user','cancelled_by_store','delivery_failed')),
    item_count INTEGER NOT NULL CHECK (item_count > 0),
    subtotal NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    delivery_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    handling_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    order_value NUMERIC(12,2) NOT NULL CHECK (order_value >= 0),
    refund_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (refund_amount >= 0),
    refund_status VARCHAR(20) NOT NULL CHECK (refund_status IN ('none','partial','full')),
    fulfillment_cost NUMERIC(10,2) NOT NULL CHECK (fulfillment_cost >= 0),
    payment_processing_cost NUMERIC(10,2) NOT NULL CHECK (payment_processing_cost >= 0),
    cancellation_actor VARCHAR(30),
    cancellation_reason VARCHAR(150),
    FOREIGN KEY (checkout_id, user_id, store_id)
        REFERENCES checkout_attempts(checkout_id, user_id, store_id),
    CHECK (ABS(order_value - (subtotal + delivery_fee + handling_fee - discount_amount)) <= 0.01),
    CHECK (refund_amount <= order_value)
);

CREATE TABLE order_items (
    order_item_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    unit_cost NUMERIC(10,2) NOT NULL CHECK (unit_cost >= 0),
    item_discount NUMERIC(10,2) NOT NULL DEFAULT 0,
    item_total NUMERIC(12,2) NOT NULL CHECK (item_total >= 0),
    was_substituted BOOLEAN NOT NULL,
    was_available_at_checkout BOOLEAN NOT NULL,
    CHECK (ABS(item_total - (unit_price * quantity - item_discount)) <= 0.01)
);

CREATE TABLE order_status_history (
    status_event_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    order_status VARCHAR(30) NOT NULL,
    status_timestamp TIMESTAMPTZ NOT NULL,
    reason_code VARCHAR(50)
);

CREATE TABLE experiment_assignments (
    assignment_id BIGINT PRIMARY KEY,
    experiment_id VARCHAR(50) NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    variant VARCHAR(20) NOT NULL CHECK (variant IN ('control','treatment')),
    assigned_at TIMESTAMPTZ NOT NULL,
    first_exposed_at TIMESTAMPTZ,
    eligibility_reason VARCHAR(100) NOT NULL,
    UNIQUE (experiment_id, user_id),
    CHECK (first_exposed_at IS NULL OR first_exposed_at >= assigned_at)
);

CREATE TABLE events (
    event_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    event_name VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    product_id BIGINT REFERENCES products(product_id),
    search_id BIGINT REFERENCES searches(search_id),
    checkout_id BIGINT REFERENCES checkout_attempts(checkout_id),
    payment_attempt_id BIGINT REFERENCES payment_attempts(payment_attempt_id),
    order_id BIGINT REFERENCES orders(order_id),
    store_id BIGINT REFERENCES stores(store_id),
    screen_name VARCHAR(50),
    event_properties JSONB NOT NULL DEFAULT '{}',
    FOREIGN KEY (session_id, user_id) REFERENCES sessions(session_id, user_id)
);

CREATE INDEX idx_sessions_user_time ON sessions(user_id, session_started_at);
CREATE INDEX idx_events_name_time_user ON events(event_name, event_timestamp, user_id);
CREATE INDEX idx_events_session_time ON events(session_id, event_timestamp);
CREATE INDEX idx_checkouts_user_time ON checkout_attempts(user_id, checkout_started_at);
CREATE INDEX idx_orders_user_time ON orders(user_id, order_placed_at);
CREATE INDEX idx_experiment_variant ON experiment_assignments(experiment_id, variant, user_id);
