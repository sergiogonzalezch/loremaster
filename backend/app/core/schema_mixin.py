from pydantic import BaseModel, ConfigDict


class FromAttributesMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
