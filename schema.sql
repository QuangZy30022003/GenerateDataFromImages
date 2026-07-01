-- Database initialization script for KOL Vendor Registration

CREATE DATABASE IF NOT EXISTS kol_vendor_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kol_vendor_db;

-- Table to store vendor registrations
CREATE TABLE IF NOT EXISTS vendors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    is_individual VARCHAR(50) DEFAULT '',
    is_customer VARCHAR(50) DEFAULT '',
    vendor_code VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    address TEXT DEFAULT NULL,
    tax_code VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(50) DEFAULT NULL,
    fax VARCHAR(50) DEFAULT NULL,
    email VARCHAR(255) DEFAULT NULL,
    website VARCHAR(255) DEFAULT NULL,
    vendor_group VARCHAR(100) NOT NULL,
    id_number VARCHAR(100) DEFAULT NULL,
    date_of_issue VARCHAR(50) DEFAULT NULL,
    place_of_issue VARCHAR(255) DEFAULT NULL,
    salutation VARCHAR(255) DEFAULT NULL,
    contact_fullname VARCHAR(255) DEFAULT NULL,
    job_title VARCHAR(255) DEFAULT NULL,
    contact_address TEXT DEFAULT NULL,
    mobile_phone VARCHAR(50) DEFAULT NULL,
    office_phone VARCHAR(50) DEFAULT NULL,
    secondary_mobile_phone VARCHAR(50) DEFAULT NULL,
    contact_email VARCHAR(255) DEFAULT NULL,
    bank_account_number VARCHAR(100) DEFAULT NULL,
    bank_name VARCHAR(255) DEFAULT NULL,
    bank_branch VARCHAR(255) DEFAULT NULL,
    bank_province VARCHAR(255) DEFAULT NULL,
    account_holder_name VARCHAR(255) DEFAULT NULL,
    date_of_birth VARCHAR(50) DEFAULT NULL,
    stt INT NOT NULL,
    communication_address TEXT DEFAULT NULL,
    link_profile VARCHAR(555) DEFAULT NULL,
    cccd_front_path VARCHAR(255) DEFAULT NULL,
    cccd_back_path VARCHAR(255) DEFAULT NULL,
    passport_path VARCHAR(255) DEFAULT NULL,
    business_license_path VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table to store logs
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vendor_code VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    tax_code VARCHAR(100) NOT NULL,
    vendor_group VARCHAR(100) NOT NULL,
    phone VARCHAR(50) DEFAULT NULL,
    email VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
