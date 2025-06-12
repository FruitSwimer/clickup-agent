from typing import TypeVar, Generic, Optional, List, Dict, Any
from pymongo.asynchronous.collection import AsyncCollection
from pydantic import BaseModel
from datetime import datetime


T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    def __init__(self, collection: AsyncCollection, model_class: type[T]):
        self.collection = collection
        self.model_class = model_class
    
    async def create(self, document: T) -> str:
        doc_dict = document.dict()
        result = await self.collection.insert_one(doc_dict)
        return str(result.inserted_id)
    
    async def create_many(self, documents: List[T]) -> List[str]:
        docs_dict = [doc.dict() for doc in documents]
        result = await self.collection.insert_many(docs_dict)
        return [str(id) for id in result.inserted_ids]
    
    async def find_by_id(self, id: str) -> Optional[T]:
        document = await self.collection.find_one({"_id": id})
        if document:
            return self.model_class(**document)
        return None
    
    async def find_one(self, filter: Dict[str, Any]) -> Optional[T]:
        document = await self.collection.find_one(filter)
        if document:
            return self.model_class(**document)
        return None
    
    async def find_many(
        self, 
        filter: Dict[str, Any] = {}, 
        skip: int = 0, 
        limit: int = 100,
        sort: Optional[List[tuple]] = None
    ) -> List[T]:
        cursor = self.collection.find(filter)
        
        if sort:
            cursor = cursor.sort(sort)
        
        cursor = cursor.skip(skip).limit(limit)
        
        documents = await cursor.to_list(length=limit)
        return [self.model_class(**doc) for doc in documents]
    
    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any]) -> bool:
        update_dict = {"$set": update}
        result = await self.collection.update_one(filter, update_dict)
        return result.modified_count > 0
    
    async def update_many(self, filter: Dict[str, Any], update: Dict[str, Any]) -> int:
        update_dict = {"$set": update}
        result = await self.collection.update_many(filter, update_dict)
        return result.modified_count
    
    async def delete_one(self, filter: Dict[str, Any]) -> bool:
        result = await self.collection.delete_one(filter)
        return result.deleted_count > 0
    
    async def delete_many(self, filter: Dict[str, Any]) -> int:
        result = await self.collection.delete_many(filter)
        return result.deleted_count
    
    async def count(self, filter: Dict[str, Any] = {}) -> int:
        return await self.collection.count_documents(filter)