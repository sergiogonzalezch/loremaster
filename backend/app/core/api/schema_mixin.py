from pydantic import BaseModel, ConfigDict


class FromAttributesMixin(BaseModel):
    """Mixin para esquemas Pydantic que permite crear modelos desde objetos ORM.

    Configura from_attributes=True para mapear atributos de objetos SQLModel/SQLAlchemy.
    """

    model_config = ConfigDict(from_attributes=True)
