from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import discord

ModalSubmitHandler = Callable[[discord.Interaction, dict[str, str]], Awaitable[None]]
ModalErrorHandler = Callable[[discord.Interaction, Exception], Awaitable[None]]


@dataclass(slots=True)
class ModalTextInputSpec:
    key: str
    label: str
    style: discord.TextStyle = discord.TextStyle.short
    placeholder: str | None = None
    default: str | None = None
    required: bool = True
    min_length: int | None = None
    max_length: int | None = None


class BuiltModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        fields: list[ModalTextInputSpec],
        on_submit_handler: ModalSubmitHandler,
        on_error_handler: ModalErrorHandler | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(title=title, timeout=timeout)
        self.on_submit_handler = on_submit_handler
        self.on_error_handler = on_error_handler
        self.inputs: dict[str, discord.ui.TextInput] = {}

        for field in fields:
            text_input = discord.ui.TextInput(
                label=field.label,
                style=field.style,
                placeholder=field.placeholder,
                default=field.default,
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
            )
            self.inputs[field.key] = text_input
            self.add_item(text_input)

    @property
    def values(self) -> dict[str, str]:
        return {key: str(text_input.value) for key, text_input in self.inputs.items()}

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.on_submit_handler(interaction, self.values)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if self.on_error_handler is not None:
            await self.on_error_handler(interaction, error)
            return

        if interaction.response.is_done():
            await interaction.followup.send(
                "Something went wrong while processing the modal.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Something went wrong while processing the modal.",
            ephemeral=True,
        )


class ModalBuilder:
    def __init__(self, title: str, *, timeout: float | None = None) -> None:
        self.title = title
        self.timeout = timeout
        self.fields: list[ModalTextInputSpec] = []

    def add_text_input(
        self,
        key: str,
        label: str,
        *,
        style: discord.TextStyle = discord.TextStyle.short,
        placeholder: str | None = None,
        default: str | None = None,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
    ) -> ModalBuilder:
        if len(self.fields) >= 5:
            raise ValueError("Discord modals can only contain up to 5 text inputs.")

        if any(field.key == key for field in self.fields):
            raise ValueError(f"Duplicate modal field key: {key}")

        self.fields.append(
            ModalTextInputSpec(
                key=key,
                label=label,
                style=style,
                placeholder=placeholder,
                default=default,
                required=required,
                min_length=min_length,
                max_length=max_length,
            )
        )
        return self

    def build(
        self,
        *,
        on_submit: ModalSubmitHandler,
        on_error: ModalErrorHandler | None = None,
    ) -> BuiltModal:
        if not self.fields:
            raise ValueError("Modal must contain at least one text input.")

        return BuiltModal(
            title=self.title,
            fields=list(self.fields),
            on_submit_handler=on_submit,
            on_error_handler=on_error,
            timeout=self.timeout,
        )
