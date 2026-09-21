-- Crear la base de datos y seleccionarla
CREATE DATABASE IF NOT EXISTS recursos_humanos;
USE recursos_humanos;

-- 1. Tabla de Departamentos (Catálogo)
CREATE TABLE departamentos (
    id_departamento INT AUTO_INCREMENT PRIMARY KEY,
    nombre_departamento VARCHAR(100) NOT NULL UNIQUE
);

-- 2. Tabla de Empleados
CREATE TABLE empleados (
    id_empleado INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_departamento INT,
    FOREIGN KEY (id_departamento) REFERENCES departamentos(id_departamento) ON DELETE SET NULL
);

-- 3. Tabla de Asistencia (Tabla de Hechos)
CREATE TABLE asistencia (
    id_asistencia INT AUTO_INCREMENT PRIMARY KEY,
    id_empleado INT NOT NULL,
    fecha_hora DATETIME NOT NULL,
    FOREIGN KEY (id_empleado) REFERENCES empleados(id_empleado) ON DELETE CASCADE
);

-- Índice para optimizar futuras consultas y vistas
CREATE INDEX idx_fecha ON asistencia(fecha_hora);