-- ============================================================
-- FILE: init.sql
-- Mục đích: Khởi tạo schema cho database rag_demo_db
-- Bảng: rag_history - Lưu lịch sử mỗi lần user gọi API /api/chat
--
-- Lưu ý: File này chỉ để tham khảo hoặc import thủ công.
-- Backend FastAPI đã tự động tạo bảng này qua SQLAlchemy
-- (Base.metadata.create_all) khi khởi động lần đầu.
-- ============================================================

CREATE DATABASE IF NOT EXISTS rag_demo_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE rag_demo_db;

CREATE TABLE IF NOT EXISTS rag_history (
    -- Khóa chính, tự tăng
    id              INT             NOT NULL AUTO_INCREMENT,

    -- Câu hỏi gốc người dùng nhập vào (từ khóa tìm kiếm)
    search_query    LONGTEXT        NOT NULL,

    -- Toàn bộ Prompt hoàn chỉnh đã ráp Context + Câu hỏi gửi sang Ollama
    generated_prompt LONGTEXT       NOT NULL,

    -- Câu trả lời cuối cùng nhận về từ mô hình AI (Ollama/llama3)
    ai_response     LONGTEXT        NOT NULL,

    -- Thời điểm ghi log (UTC)
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE real_estate_dataset ( -- PostgreSql syntax
    -- 1. IDENTIFICATION & MANAGEMENT
    id SERIAL PRIMARY KEY,
    property_code VARCHAR(50) UNIQUE NOT NULL,

    -- 2. GEOGRAPHIC POSITIONING (GPS & Address)
    latitude NUMERIC(10, 8) NOT NULL,   -- Example: 10.792431
    longitude NUMERIC(11, 8) NOT NULL,  -- Example: 106.674921
    province VARCHAR(50) DEFAULT 'Thành phố Hồ Chí Minh',
    district VARCHAR(50) NOT NULL,
    ward VARCHAR(50) NOT NULL,
    street_name VARCHAR(100) NOT NULL,  -- Kept for Ollama reporting
    house_number VARCHAR(50),           -- Optional, for transparency

    -- 3. SPATIAL DERIVED FEATURES (For XGBoost Advanced Learning)
    neighbor_avg_price_per_m2 NUMERIC(6, 3), -- Average price (Billion VND/m2) within 200m-500m radius
    distance_to_center_km NUMERIC(5, 2),     -- Straight-line distance to District 1 / Ben Thanh Market
    regional_transaction_density INT DEFAULT 0, -- Number of successful deals nearby (liquidity indicator)

    -- 4. PHYSICAL & GEOMETRIC PROPERTIES
    land_area NUMERIC(10, 2) NOT NULL,       -- Certified land area on the title deed (m2)
    usable_area NUMERIC(10, 2),             -- Actual total floor area (m2)
    width NUMERIC(5, 2),                    -- Frontage width (m) - Critical pricing factor in VN
    length NUMERIC(5, 2),                   -- Depth of the property (m)
    total_floors INT DEFAULT 1,
    bedroom_count INT DEFAULT 0,
    bathroom_count INT DEFAULT 0,
    house_direction VARCHAR(20),            -- North, South, East, West, Southeast, etc.
    construction_year INT,                  -- To calculate asset depreciation

    -- 5. ALLEY & FRONTAGE CHARACTERISTICS (Crucial for alley houses)
    location_type INT NOT NULL,             -- 1: Street front, 2: Car alley, 3: Tricycle alley, 4: Motorbike alley
    alley_width_m NUMERIC(4, 2) DEFAULT 0.0, -- Actual alley width in front of the house (m)
    distance_to_main_street_m INT,          -- Distance to the main road
    is_dead_end_alley BOOLEAN DEFAULT FALSE, -- True if it's a cul-de-sac (usually lowers the price)

    -- 6. LEGAL & PLANNING STATUS
    legal_status INT NOT NULL,              -- 1: Separate pink book, 2: Shared pink book, 3: Hand paper
    is_subject_to_planning BOOLEAN DEFAULT FALSE, -- True if affected by zoning/public projects
    planning_encroachment_depth_m NUMERIC(4, 2) DEFAULT 0, -- Depth lost if the alley is widened

    -- 7. TARGET VARIABLE (For XGBoost Prediction)
    raw_price_billion NUMERIC(6, 3) NOT NULL, -- Target price in Billion VND (e.g., 6.100 means 6.1 Billion)
    
    -- 8. TIMESTAMPS
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE real_estate_dataset ( -- MySQL syntax
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_code VARCHAR(50) UNIQUE NOT NULL,

    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,

    province VARCHAR(50) DEFAULT 'Thành phố Hồ Chí Minh',
    district VARCHAR(50) NOT NULL,
    ward VARCHAR(50) NOT NULL,
    street_name VARCHAR(100) NOT NULL,
    house_number VARCHAR(50),

    neighbor_avg_price_per_m2 DECIMAL(6,3),
    distance_to_center_km DECIMAL(5,2),
    regional_transaction_density INT DEFAULT 0,

    land_area DECIMAL(10,2) NOT NULL,
    usable_area DECIMAL(10,2),

    width DECIMAL(5,2),
    length DECIMAL(5,2),

    total_floors INT DEFAULT 1,
    bedroom_count INT DEFAULT 0,
    bathroom_count INT DEFAULT 0,

    house_direction VARCHAR(20),
    construction_year INT,

    location_type INT NOT NULL,

    alley_width_m DECIMAL(4,2) DEFAULT 0.00,
    distance_to_main_street_m INT,

    is_dead_end_alley BOOLEAN DEFAULT FALSE,

    legal_status INT NOT NULL,

    is_subject_to_planning BOOLEAN DEFAULT FALSE,
    planning_encroachment_depth_m DECIMAL(4,2) DEFAULT 0.00,

    raw_price_billion DECIMAL(6,3) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tạo data giả:
DELIMITER $$

CREATE PROCEDURE GenerateRealEstateData()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_latitude NUMERIC(10, 8);
    DECLARE v_longitude NUMERIC(11, 8);
    DECLARE v_district VARCHAR(50);
    DECLARE v_ward VARCHAR(50);
    DECLARE v_street VARCHAR(100);
    DECLARE v_base_price_m2 NUMERIC(6, 3); -- Giá gốc theo khu vực (Tỷ/m2)
    DECLARE v_land_area NUMERIC(10, 2);
    DECLARE v_width NUMERIC(5, 2);
    DECLARE v_length NUMERIC(5, 2);
    DECLARE v_floors INT;
    DECLARE v_location_type INT;
    DECLARE v_alley_width NUMERIC(4, 2);
    DECLARE v_is_dead_end INT;
    DECLARE v_calculated_price NUMERIC(6, 3);

    -- Vòng lặp tạo 5.000 dòng dữ liệu
    WHILE i <= 5000 DO
        
        -- 1. Giả lập Phân bổ Khu vực & Tọa độ thực tế tại TP.HCM (Tập trung 3 quận đại diện)
        CASE ELT(FLOOR(1 + RAND() * 3), 1, 2, 3)
            WHEN 1 THEN 
                SET v_district = 'Quận 1';
                SET v_ward = CONCAT('Phường Bến Nghé, Q1');
                SET v_street = ELT(FLOOR(1 + RAND() * 3), 'Nguyễn Huệ', 'Lê Lợi', 'Đồng Khởi');
                -- Tọa độ trung tâm Q1 quanh mốc 10.77, 106.70
                SET v_latitude = 10.770000 + (RAND() - 0.5) * 0.01;
                SET v_longitude = 106.700000 + (RAND() - 0.5) * 0.01;
                SET v_base_price_m2 = 0.450; -- Khoảng 450 triệu/m2 gốc
            WHEN 2 THEN 
                SET v_district = 'Quận Phú Nhuận';
                SET v_ward = CONCAT('Phường 12, PN');
                SET v_street = ELT(FLOOR(1 + RAND() * 3), 'Lê Văn Sỹ', 'Phan Xích Long', 'Huỳnh Văn Bánh');
                -- Tọa độ Phú Nhuận quanh mốc 10.79, 106.67
                SET v_latitude = 10.790000 + (RAND() - 0.5) * 0.01;
                SET v_longitude = 106.670000 + (RAND() - 0.5) * 0.01;
                SET v_base_price_m2 = 0.180; -- Khoảng 180 triệu/m2 gốc
            ELSE 
                SET v_district = 'Quận Tân Bình';
                SET v_ward = CONCAT('Phường 2, TB');
                SET v_street = ELT(FLOOR(1 + RAND() * 3), 'Cộng Hòa', 'Trường Chinh', 'Phổ Quang');
                -- Tọa độ Tân Bình quanh mốc 10.80, 106.65
                SET v_latitude = 10.800000 + (RAND() - 0.5) * 0.01;
                SET v_longitude = 106.650000 + (RAND() - 0.5) * 0.01;
                SET v_base_price_m2 = 0.110; -- Khoảng 110 triệu/m2 gốc
        END CASE;

        -- 2. Giả lập Thông số hình học thực tế (Chiều ngang từ 3m-6m, chiều dài từ 8m-20m)
        SET v_width = ROUND(3.0 + RAND() * 3.0, 2);
        SET v_length = ROUND(8.0 + RAND() * 12.0, 2);
        SET v_land_area = ROUND(v_width * v_length, 2);
        SET v_floors = FLOOR(1 + RAND() * 5); -- Nhà từ 1 đến 5 tầng

        -- 3. Giả lập Loại vị trí (Hẻm hóc)
        SET v_location_type = FLOOR(1 + RAND() * 4); -- 1: Mặt tiền -> 4: Hẻm xe máy
        IF v_location_type = 1 THEN
            SET v_alley_width = 0.0;
            SET v_is_dead_end = 0;
        ELSE
            SET v_alley_width = ROUND(2.0 + RAND() * 5.0, 1); -- Hẻm rộng từ 2m đến 7m
            SET v_is_dead_end = IF(RAND() > 0.7, 1, 0); -- 30% tỷ lệ hẻm cụt
        END IF;

        -- 4. Thuật toán cấu trúc Giá thực tế (Để XGBoost có thể học được logic quy luật)
        -- Công thức thô: Giá = (Diện tích * Giá vùng m2) * Hệ số tầng * Hệ số vị trí * Hệ số hẻm cụt
        SET v_calculated_price = v_land_area * v_base_price_m2;
        SET v_calculated_price = v_calculated_price * (1 + (v_floors * 0.15)); -- Thêm tầng tăng 15% giá trị xây dựng
        
        IF v_location_type = 1 THEN 
            SET v_calculated_price = v_calculated_price * 1.4; -- Mặt tiền tăng 40% giá
        ELSEIF v_location_type = 4 OR v_alley_width < 3.0 THEN 
            SET v_calculated_price = v_calculated_price * 0.7; -- Hẻm nhỏ giảm 30% giá
        END IF;

        IF v_is_dead_end = 1 THEN 
            SET v_calculated_price = v_calculated_price * 0.9; -- Hẻm cụt bị giảm tiếp 10% giá
        END IF;
        
        -- Thêm một chút nhiễu thị trường (Market Noise) +/- 5% để model không bị học vẹt (Overfitting)
        SET v_calculated_price = ROUND(v_calculated_price * (0.95 + RAND() * 0.1), 3);

        -- 5. Thực thi lệnh INSERT vào bảng
        INSERT INTO real_estate_dataset (
            property_code, latitude, longitude, district, ward, street_name, 
            neighbor_avg_price_per_m2, distance_to_center_km, land_area, usable_area, 
            width, length, total_floors, bedroom_count, bathroom_count, 
            location_type, alley_width_m, is_dead_end_alley, legal_status, raw_price_billion
        ) VALUES (
            CONCAT('BĐS-', 100000 + i),
            v_latitude,
            v_longitude,
            v_district,
            v_ward,
            v_street,
            ROUND(v_base_price_m2 * (0.9 + RAND() * 0.2), 3), -- Giá hàng xóm quanh giá gốc
            ROUND(1.0 + RAND() * 8.0, 2), -- Khoảng cách đến trung tâm
            v_land_area,
            ROUND(v_land_area * v_floors * 0.9, 2), -- Diện tích sử dụng
            v_width,
            v_length,
            v_floors,
            v_floors + FLOOR(RAND() * 2), -- Số phòng ngủ tương ứng số tầng
            v_floors,
            v_location_type,
            v_alley_width,
            v_is_dead_end,
            IF(RAND() > 0.1, 1, 2), -- 90% là sổ hồng riêng (1), 10% là sổ chung (2)
            v_calculated_price
        );

        SET i = i + 1;
    END WHILE;
END$$

DELIMITER ;

-- KÍCH HOẠT CHẠY THỦ TỤC ĐỂ ĐỔ 5.000 DÒNG DATA
CALL GenerateRealEstateData();

-- XÓA THỦ TỤC SAU KHI ĐÃ TẠO XONG DATA
DROP PROCEDURE IF EXISTS GenerateRealEstateData;