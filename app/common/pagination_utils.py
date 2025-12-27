import json
from math import ceil
from typing import Type, TypeVar

from sqlalchemy import MetaData
from sqlalchemy.orm import Query

from app.schemas.pagination import PageDto, PageMetaDto, PageOptionsDto, ResponseCommon

T = TypeVar("T")


class PaginationHelper:
    """Helper class for creating paginated responses"""

    @staticmethod
    def create_meta(page: int, page_size: int, total_items: int) -> PageMetaDto:
        """
        Create pagination metadata

        Args:
            page: Current page number
            page_size: Items per page
            total_items: Total number of items

        Returns:
            PageMetaDto with calculated values
        """
        page_count = ceil(total_items / page_size) if page_size > 0 else 0

        return PageMetaDto(
            page=page,
            page_size=page_size,
            item_count=total_items,
            page_count=page_count,
            has_previous_page=page > 1,
            has_next_page=page < page_count,
        )

    @staticmethod
    def paginate_query(
        query: Query, page_options: PageOptionsDto, response_model: Type[T]
    ) -> PageDto[T]:
        """
        Apply pagination to a SQLAlchemy query

        Args:
            query: SQLAlchemy query object
            page_options: Pagination options from request
            response_model: Pydantic model for response items

        Returns:
            PageDto with paginated data and metadata
        """
        # If dropdown mode, return all items
        if page_options.is_dropdown:
            items = query.all()
            data = [PaginationHelper._convert_to_model(item, response_model) for item in items]
            return PageDto(
                data=data,
                meta=PageMetaDto(
                    page=1,
                    page_size=len(items),
                    item_count=len(items),
                    page_count=1,
                    has_previous_page=False,
                    has_next_page=False,
                ),
            )

        # Get total count
        total_items = query.count()

        # Calculate offset
        offset = (page_options.page - 1) * page_options.page_size

        # Apply pagination
        items = query.offset(offset).limit(page_options.page_size).all()

        # Create metadata
        meta = PaginationHelper.create_meta(
            page=page_options.page,
            page_size=page_options.page_size,
            total_items=total_items,
        )

        # Convert to response models
        data = [PaginationHelper._convert_to_model(item, response_model) for item in items]

        return PageDto(data=data, meta=meta)

    @staticmethod
    def _convert_to_model(item, response_model: Type[T]) -> T:
        if isinstance(item, response_model):
            return item

        item_dict = None
        if hasattr(item, "__table__") and hasattr(item.__table__, "columns"):
            item_dict = {column.key: getattr(item, column.key) for column in item.__table__.columns}
        else:
            try:
                item_dict = dict(item)
            except Exception:
                item_dict = item

        if isinstance(item_dict, dict):
            if "result" in item_dict and item_dict["result"]:
                if isinstance(item_dict["result"], str):
                    try:
                        item_dict["result"] = json.loads(item_dict["result"])
                    except (json.JSONDecodeError, TypeError):
                        pass

            metadata_value = None
            if "metadata_json" in item_dict:
                metadata_value = item_dict.get("metadata_json")
            elif hasattr(item, "metadata_json"):
                metadata_value = getattr(item, "metadata_json")

            if metadata_value is not None:
                if "metadata" not in item_dict or isinstance(item_dict.get("metadata"), MetaData):
                    item_dict["metadata"] = metadata_value

            if "metadata" in item_dict and isinstance(item_dict["metadata"], MetaData):
                item_dict["metadata"] = None

            fields = getattr(response_model, "model_fields", None) or getattr(
                response_model, "__fields__", None
            )
            if fields:
                if "job_id" in fields and "job_id" not in item_dict and "id" in item_dict:
                    item_dict["job_id"] = item_dict["id"]
                if (
                    "metadata" in fields
                    and "metadata" not in item_dict
                    and "metadata_json" in item_dict
                ):
                    item_dict["metadata"] = item_dict["metadata_json"]

                allowed_keys = set(fields.keys())
                item_dict = {key: value for key, value in item_dict.items() if key in allowed_keys}

            validator = getattr(response_model, "model_validate", None)
            if validator:
                return validator(item_dict)
            return response_model.parse_obj(item_dict)

        validator = getattr(response_model, "model_validate", None)
        if validator:
            return validator(item)
        return response_model.parse_obj(item)

    @staticmethod
    def create_response(
        paginated_data: PageDto[T], message: str = "SUCCESSFULLY", code: int = 200
    ) -> ResponseCommon[PageDto[T]]:
        """
        Wrap paginated data in ResponseCommon

        Args:
            paginated_data: PageDto containing data and metadata
            message: Success message
            code: HTTP status code

        Returns:
            ResponseCommon wrapper
        """
        return ResponseCommon(
            code=code,
            success=True,
            message=message,
            data=paginated_data,
        )
