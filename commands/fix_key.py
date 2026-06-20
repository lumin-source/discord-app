from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

import discord
from discord.ext import commands

from modules.embed_builder import EmbedBuilder
from modules.modal_builder import ModalBuilder


LUARMOR_API_BASE = "https://api.luarmor.net/v3"


def looks_like_html(value: str) -> bool:
    text = value.strip().lower()
    return text.startswith("<!doctype html") or text.startswith("<html")


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    timeout: int = 20,
) -> tuple[int, dict[str, object] | None, str | None]:
    payload = None
    request_headers = dict(headers or {})

    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(
        url=url,
        data=payload,
        headers=request_headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
            if not raw_text:
                return response.status, None, None
            return response.status, json.loads(raw_text), None
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        if not error_text:
            return exc.code, None, None

        try:
            return exc.code, json.loads(error_text), None
        except json.JSONDecodeError:
            return exc.code, None, error_text
    except urllib.error.URLError as exc:
        return 0, None, str(exc.reason)


class FixKeyView(discord.ui.View):
    def __init__(self, cog: "FixKey") -> None:
        super().__init__(timeout=600)
        self.cog = cog

        self.add_item(
            discord.ui.Button(
                label="Purchase",
                style=discord.ButtonStyle.link,
                url="https://lumin-rocks.mysellauth.com/",
            )
        )

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.secondary)
    async def get_script(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button
        script = '```lua\nloadstring(game:HttpGet("https://lumin.rest/"))()\n```'
        await interaction.response.send_message(script, ephemeral=True)

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.primary)
    async def reset_hwid_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button

        async def on_submit(
            modal_interaction: discord.Interaction, values: dict[str, str]
        ) -> None:
            user_key_value = values.get("user_key", "").strip()

            if not user_key_value:
                await modal_interaction.response.send_message(
                    "Your key is required, please try again.",
                    ephemeral=True,
                )
                return

            await modal_interaction.response.defer(ephemeral=True, thinking=True)
            success, message = await self.cog.reset_hwid(user_key_value)

            if success:
                next_reset = int((datetime.now(UTC) + timedelta(days=1)).timestamp())
                await modal_interaction.followup.send(
                    (
                        "HWID reset successful!\n"
                        f"You can reset it again at <t:{next_reset}:F> (<t:{next_reset}:R>)."
                    ),
                    ephemeral=True,
                )
                return

            await modal_interaction.followup.send(
                f"Could not reset HWID for the following reason: \"{message}\"",
                ephemeral=True,
            )

        modal = (
            ModalBuilder("Reset HWID")
            .add_text_input(
                "user_key",
                "Your Key",
                placeholder="Enter your key here.",
                required=True,
                max_length=32,
            )
            .build(on_submit=on_submit)
        )
        await interaction.response.send_modal(modal)


class FixKey(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.project_id_override: str | None = os.getenv("LUARMOR_PROJECT_ID")
        self.project_id_cache: dict[str, str] = {}

    async def resolve_project_id(self, api_key: str) -> tuple[str | None, str | None]:
        if self.project_id_override:
            return self.project_id_override, None

        cached_project_id = self.project_id_cache.get(api_key)
        if cached_project_id:
            return cached_project_id, None

        encoded_api_key = urllib.parse.quote(api_key, safe="")
        details_url = f"{LUARMOR_API_BASE}/keys/{encoded_api_key}/details"
        status, data, request_error = await asyncio.to_thread(
            request_json,
            "GET",
            details_url,
        )

        if request_error:
            lowered = request_error.lower()
            if looks_like_html(request_error) or "not authorized" in lowered:
                return (
                    None,
                    "Luarmor request was blocked as Unauthorized. Whitelist this server IP in your Luarmor dashboard and verify LUARMOR_KEY.",
                )
            return None, f"Request failed while resolving project: {request_error}"

        if status in (401, 403):
            return (
                None,
                "Luarmor API rejected authorization while resolving project. Verify LUARMOR_KEY and whitelist this server IP.",
            )

        if status != 200 or not isinstance(data, dict):
            return None, "Could not fetch project details from Luarmor API."

        projects = data.get("projects", [])
        if not isinstance(projects, list) or not projects:
            return None, "No projects were returned for this API key."

        product_name = os.getenv("PRODUCT_NAME", "").strip().lower()
        if product_name:
            for project in projects:
                if not isinstance(project, dict):
                    continue

                project_name = str(project.get("name", "")).strip().lower()
                if project_name == product_name:
                    project_id = str(project.get("id", "")).strip()
                    if project_id:
                        self.project_id_cache[api_key] = project_id
                        return project_id, None

        first_project = projects[0]
        if isinstance(first_project, dict):
            project_id = str(first_project.get("id", "")).strip()
            if project_id:
                self.project_id_cache[api_key] = project_id
                return project_id, None

        return None, "Could not determine project ID from Luarmor API response."

    async def reset_hwid(self, user_key: str) -> tuple[bool, str]:
        api_key = os.getenv("LUARMOR_KEY", "").strip()
        if not api_key:
            return False, "LUARMOR_KEY is not configured in .env."

        project_id, project_error = await self.resolve_project_id(api_key)
        if not project_id:
            return False, project_error or (
                "Could not resolve project ID. Set LUARMOR_PROJECT_ID in .env or verify PRODUCT_NAME."
            )

        reset_url = f"{LUARMOR_API_BASE}/projects/{project_id}/users/resethwid"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        body = {"user_key": user_key}

        status, data, request_error = await asyncio.to_thread(
            request_json,
            "POST",
            reset_url,
            headers=headers,
            body=body,
        )

        if request_error:
            lowered = request_error.lower()
            if looks_like_html(request_error) or "not authorized" in lowered:
                return (
                    False,
                    "Luarmor rejected the reset request as Unauthorized. Whitelist this server IP in Luarmor dashboard and verify LUARMOR_KEY.",
                )
            return False, f"Request failed: {request_error}"

        if status in (401, 403):
            return (
                False,
                "Luarmor API returned Unauthorized/Forbidden. Verify LUARMOR_KEY and whitelist this server IP.",
            )

        if status == 429:
            return False, "Luarmor API rate limit hit. Please try again in a minute."

        if isinstance(data, dict):
            message = str(data.get("message", "Unknown response"))
            success = bool(data.get("success", False))
            if success and status == 200:
                return True, message
            return False, message

        return False, f"Unexpected API response (status {status})."

    @commands.hybrid_command(
        name="fix-key",
        description="Shows key troubleshooting steps and lets you reset HWID.",
    )
    async def fix_key(self, ctx: commands.Context) -> None:
        next_reset = int((datetime.now(UTC) + timedelta(days=3)).timestamp())
        embed = (
            EmbedBuilder(
                title="Troubleshooting Key Issues",
                description=(
                    "If your key does not work, please attempt the following to reset it:\n"
                    "- Press the Reset HWID button below and enter your key.\n"
                    "- After resetting, immediately try your key again to set the new HWID.\n"
                    "- If it *still* doesn't work, create a ticket in <#1508165069635063998>.\n"
                    "### You are going to be banned if you make a ticket and leave it blank."
                ),
                color=discord.Color.blurple(),
            )
            .set_timestamp()
            .build()
        )

        await ctx.reply(embed=embed, view=FixKeyView(self))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FixKey(bot))
