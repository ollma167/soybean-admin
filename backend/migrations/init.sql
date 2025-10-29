-- Initialize database schema

-- Create templates table
CREATE TABLE IF NOT EXISTS templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_name (name),
    INDEX idx_active (is_active),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create template_combos table
CREATE TABLE IF NOT EXISTS template_combos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    template_id INT NOT NULL,
    prefix VARCHAR(100) NOT NULL,
    sort_order INT DEFAULT 0,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
    INDEX idx_template (template_id),
    INDEX idx_prefix (prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create combo_items table
CREATE TABLE IF NOT EXISTS combo_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    combo_id INT NOT NULL,
    product_code VARCHAR(255) NOT NULL,
    quantity INT DEFAULT 1,
    sale_price DECIMAL(10, 4) DEFAULT 1.0000,
    base_price DECIMAL(10, 4) DEFAULT 1.0000,
    cost_price DECIMAL(10, 4) DEFAULT 1.0000,
    FOREIGN KEY (combo_id) REFERENCES template_combos(id) ON DELETE CASCADE,
    INDEX idx_combo (combo_id),
    INDEX idx_product (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create operation_logs table
CREATE TABLE IF NOT EXISTS operation_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_action (user_id, action),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert initial data (optional)
-- You can add some sample templates here if needed
