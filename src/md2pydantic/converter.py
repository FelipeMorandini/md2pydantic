"""MDConverter - the main public API for md2pydantic."""

from __future__ import annotations

from typing import Generic, Literal, overload

from pydantic import BaseModel

from md2pydantic.models import (
    BlockLocation,
    BlockType,
    ExtractionError,
    ExtractionErrorDetail,
    ModelValidationError,
    PartialResult,
    RowLocation,
    T,
    TransformError,
)
from md2pydantic.parser import scan_blocks, scan_tables
from md2pydantic.transformers import block_to_dict, table_to_dicts
from md2pydantic.validators import validate_dict, validate_dicts


class MDConverter(Generic[T]):
    """Extract structured data from Markdown into Pydantic models.

    Usage::

        users = MDConverter(User).parse_tables(markdown)
        config = MDConverter(Config).parse_json(markdown)
        data = MDConverter(Item).parse(markdown)
    """

    def __init__(self, model: type[T]) -> None:
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            raise TypeError(
                f"model must be a Pydantic BaseModel subclass, got {model!r}"
            )
        self.model = model

    @overload
    def parse_tables(
        self,
        markdown: str,
        *,
        index: int | None = ...,
        heading: str | None = ...,
        partial: Literal[False] = ...,
    ) -> list[T]: ...

    @overload
    def parse_tables(
        self,
        markdown: str,
        *,
        index: int | None = ...,
        heading: str | None = ...,
        partial: Literal[True] = ...,
    ) -> PartialResult[T]: ...

    def parse_tables(
        self,
        markdown: str,
        *,
        index: int | None = None,
        heading: str | None = None,
        partial: bool = False,
    ) -> list[T] | PartialResult[T]:
        """Extract tables from markdown and return validated model instances.

        Args:
            markdown: The Markdown text to parse.
            index: If provided, only parse the table at this 0-based index
                (applied after heading filtering).
            heading: If provided, only parse tables under headings matching
                this substring (case-insensitive).
            partial: If True, return a PartialResult containing both
                successes and errors instead of raising on failure.

        Returns:
            List of validated model instances, or PartialResult when
            partial=True.

        Raises:
            ExtractionError: If no tables are found or no rows validate
                (only when partial=False).
        """
        tables = scan_tables(markdown, index=index, heading=heading)
        if not tables:
            if partial:
                return PartialResult(data=[], errors=[])
            raise ExtractionError("No tables found in markdown")

        results: list[T] = []
        all_errors: list[ExtractionErrorDetail] = []

        for table_idx, table in enumerate(tables):
            dicts = table_to_dicts(table)
            validations = validate_dicts(dicts, self.model)
            for row_idx, v in enumerate(validations):
                if v.data is not None:
                    results.append(v.data)
                else:
                    all_errors.append(
                        ModelValidationError(
                            field_errors=v.errors,
                            location=RowLocation(
                                table_index=table_idx,
                                row_index=row_idx,
                                table_heading=table.heading,
                                start_line=table.start_line,
                            ),
                            raw_input=v.raw_input,
                        )
                    )

        if partial:
            return PartialResult(data=results, errors=all_errors)

        if not results:
            raise ExtractionError("No table rows matched the model", errors=all_errors)

        return results

    def parse_json(self, markdown: str) -> T:
        """Extract a JSON block from markdown and return a validated model.

        Tries each JSON block in document order, returning the first
        that validates against the model.

        Note:
            The ``partial`` parameter is not supported for code block
            methods since they return a single model instance. Use
            ``parse(partial=True)`` for partial-result semantics.

        Raises:
            ExtractionError: If no JSON blocks are found or none validate.
        """
        return self._parse_code_blocks(markdown, BlockType.JSON)

    def parse_yaml(self, markdown: str) -> T:
        """Extract a YAML block from markdown and return a validated model.

        Tries each YAML block in document order, returning the first
        that validates against the model.

        Note:
            The ``partial`` parameter is not supported for code block
            methods since they return a single model instance. Use
            ``parse(partial=True)`` for partial-result semantics.

        Raises:
            ExtractionError: If no YAML blocks are found or none validate.
        """
        return self._parse_code_blocks(markdown, BlockType.YAML)

    @overload
    def parse(
        self,
        markdown: str,
        *,
        partial: Literal[False] = ...,
    ) -> T | list[T]: ...

    @overload
    def parse(
        self,
        markdown: str,
        *,
        partial: Literal[True] = ...,
    ) -> PartialResult[T]: ...

    def parse(
        self,
        markdown: str,
        *,
        partial: bool = False,
    ) -> T | list[T] | PartialResult[T]:
        """Auto-detect format and parse structured data from markdown.

        Tries code blocks (JSON/YAML) first, then tables. Returns a
        single model instance for code blocks or a list for tables.

        When ``partial=True``, always returns a ``PartialResult`` where
        ``data`` is a list (even for single code block results, which
        are wrapped in a 1-element list for consistency).

        Args:
            markdown: The Markdown text to parse.
            partial: If True, return a PartialResult containing both
                successes and errors instead of raising on failure.

        Raises:
            ExtractionError: If no structured data is found
                (only when partial=False).
        """
        blocks = scan_blocks(markdown)
        all_errors: list[ExtractionErrorDetail] = []

        # Try code blocks first (more precise)
        if blocks:
            for block_idx, block in enumerate(blocks):
                location = BlockLocation(
                    start_line=block.start_line,
                    end_line=block.end_line,
                    block_type=block.block_type,
                    block_index=block_idx,
                )
                result = block_to_dict(block)
                if result.data is None:
                    all_errors.append(
                        TransformError(
                            message=result.error or "Unknown transform error",
                            location=location,
                            raw_content=result.raw_content,
                        )
                    )
                    continue

                data = result.data
                if isinstance(data, dict):
                    validation = validate_dict(data, self.model)
                    if validation.data is not None:
                        if partial:
                            return PartialResult(
                                data=[validation.data], errors=all_errors
                            )
                        return validation.data
                    all_errors.append(
                        ModelValidationError(
                            field_errors=validation.errors,
                            location=location,
                            raw_input=validation.raw_input,
                        )
                    )
                elif isinstance(data, list):
                    # JSON/YAML array: validate all dict elements,
                    # return those that match
                    validated: list[T] = []
                    for item in data:
                        if isinstance(item, dict):
                            v = validate_dict(item, self.model)
                            if v.data is not None:
                                validated.append(v.data)
                            else:
                                all_errors.append(
                                    ModelValidationError(
                                        field_errors=v.errors,
                                        location=location,
                                        raw_input=v.raw_input,
                                    )
                                )
                    if validated:
                        if partial:
                            return PartialResult(data=validated, errors=all_errors)
                        return validated

        # Fall back to tables (lazy — only scanned if code blocks fail)
        tables = scan_tables(markdown)
        if tables:
            results: list[T] = []
            for table_idx, table in enumerate(tables):
                dicts = table_to_dicts(table)
                validations = validate_dicts(dicts, self.model)
                for row_idx, v in enumerate(validations):
                    if v.data is not None:
                        results.append(v.data)
                    else:
                        all_errors.append(
                            ModelValidationError(
                                field_errors=v.errors,
                                location=RowLocation(
                                    table_index=table_idx,
                                    row_index=row_idx,
                                    table_heading=table.heading,
                                    start_line=table.start_line,
                                ),
                                raw_input=v.raw_input,
                            )
                        )
            if results:
                if partial:
                    return PartialResult(data=results, errors=all_errors)
                return results

        if partial:
            return PartialResult(data=[], errors=all_errors)

        if all_errors:
            raise ExtractionError(
                "Structured data found but none matched the model",
                errors=all_errors,
            )
        raise ExtractionError("No structured data found in markdown")

    def _parse_code_blocks(self, markdown: str, block_type: BlockType) -> T:
        """Parse code blocks of a specific type and return validated model."""
        blocks = scan_blocks(markdown)
        typed_blocks = [b for b in blocks if b.block_type == block_type]
        if not typed_blocks:
            raise ExtractionError(
                f"No {block_type.value.upper()} blocks found in markdown"
            )

        all_errors: list[ExtractionErrorDetail] = []
        for block_idx, block in enumerate(typed_blocks):
            location = BlockLocation(
                start_line=block.start_line,
                end_line=block.end_line,
                block_type=block.block_type,
                block_index=block_idx,
            )
            result = block_to_dict(block)
            if result.data is None:
                all_errors.append(
                    TransformError(
                        message=result.error or "Unknown transform error",
                        location=location,
                        raw_content=result.raw_content,
                    )
                )
                continue

            data = result.data
            if isinstance(data, dict):
                validation = validate_dict(data, self.model)
                if validation.data is not None:
                    return validation.data
                all_errors.append(
                    ModelValidationError(
                        field_errors=validation.errors,
                        location=location,
                        raw_input=validation.raw_input,
                    )
                )
            elif isinstance(data, list):
                # JSON/YAML array: try each dict element, return first match
                for item in data:
                    if isinstance(item, dict):
                        validation = validate_dict(item, self.model)
                        if validation.data is not None:
                            return validation.data
                        all_errors.append(
                            ModelValidationError(
                                field_errors=validation.errors,
                                location=location,
                                raw_input=validation.raw_input,
                            )
                        )

        raise ExtractionError(
            f"No {block_type.value.upper()} block matched the model",
            errors=all_errors,
        )
