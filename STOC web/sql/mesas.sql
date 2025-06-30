CREATE TABLE IF NOT EXISTS mesas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero INT NOT NULL,
    status ENUM('livre', 'ocupada') NOT NULL DEFAULT 'livre'
);
