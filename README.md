# 📜 Lore Master API

Lore Master es el backend central de una plataforma web interactiva diseñada para escritores, narradores de rol (RPG) y creadores de contenido. Permite construir, organizar y expandir mundos ficticios utilizando una arquitectura RAG (Retrieval-Augmented Generation) basada en documentos de los propios usuarios.

## 🚀 Estado Actual (Draft - Semana 1)
Este repositorio contiene la versión inicial (Draft) de la API. Actualmente incluye la estructura base, validación de datos, manejo de subida de archivos y la configuración local de la base de datos vectorial.

### 🛠️ Stack Tecnológico
* **Framework Web:** FastAPI (Python)
* **Base de Datos Vectorial:** Qdrant (Modo Local / En memoria)
* **Validación de Datos:** Pydantic
* **Entorno:** `python-dotenv`

---

## ⚙️ Requisitos Previos
Asegúrate de tener instalado en tu sistema:
* [Python 3.10+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/)

---

## 💻 Instalación y Configuración Local

**1. Clonar el repositorio y entrar al backend**
```bash
git clone https://github.com/sergiogonzalezch/loremaster
cd lore-master/backend

# En Windows:
python -m venv venv
venv\Scripts\activate

# En Mac / Linux:
python3 -m venv venv
source venv/bin/activate

# Instalar requerimiento
pip install -r requirements.txt

# Variables de entorno
PROJECT_NAME="Lore Master API"
ENVIRONMENT="development"

# Ejecutar
uvicorn main:app --reload