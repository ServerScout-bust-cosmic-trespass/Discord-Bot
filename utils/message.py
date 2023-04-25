"""Useful functions for sending messages to the user."""

import base64
from typing import List, Optional

import interactions
import mcstatus
from interactions import ActionRow

from .database import Database
from .logger import Logger
from .text import Text


class Message:
    def __init__(
        self,
        logger: "Logger",
        db: "Database",
        text: "Text",
    ):
        self.logger = logger
        self.db = db
        self.text = text

        self.RED = 0xFF0000  # error
        self.GREEN = 0x00FF00  # success
        self.YELLOW = 0xFFFF00  # warning
        self.BLUE = 0x0000FF  # info
        self.PINK = 0xFFC0CB  # offline

    @staticmethod
    def buttons(*args) -> list[ActionRow]:
        """Return disabled buttons

        Args:
            *args (bool): The buttons to disable, len must be 3

        Returns:
            [
                interactions.ActionRow(): Next, Previous
                interactions.ActionRow(): Show Players
            ]
        """
        disabled = list(*args) if len(args) == 3 else [False, False, False]

        # button: Next, Previous, Show Players
        rows = [
            interactions.ActionRow(
                interactions.Button(
                    label="Next",
                    style=interactions.ButtonStyle.PRIMARY,
                    custom_id="next",
                    disabled=disabled[0],
                ),
                interactions.Button(
                    label="Previous",
                    style=interactions.ButtonStyle.PRIMARY,
                    custom_id="previous",
                    disabled=disabled[1],
                ),
            ),
            interactions.ActionRow(
                interactions.Button(
                    label="Show Players",
                    style=interactions.ButtonStyle.PRIMARY,
                    custom_id="players",
                    disabled=disabled[2],
                ),
            ),
        ]

        return rows

    def embed(
        self,
        pipeline: list,
        index: int,
    ) -> Optional[dict]:
        """Return an embed

        Args:
            pipeline (list): The pipeline to use
            index (int): The index of the embed

        Returns:
            {
                "embed": interactions.Embed, # The embed
                "components": [interactions.ActionRow], # The buttons
            }
        """

        total_servers = self.db.countPipeline(pipeline)

        if total_servers == 0:
            return

        if index >= total_servers:
            index = 0

        data = self.db.get_doc_at_index(pipeline, index)

        if data is None:
            return {
                "embed": self.standardEmbed(
                    title="Error",
                    description="No server found",
                    color=self.YELLOW,
                ),
                "components": self.buttons(True, True, True),
            }

        isOnline = "🔴"
        try:
            mcstatus.JavaServer(data["host"]["ip"], data["host"]["port"]).ping()
            isOnline = "🟢"
            self.logger.debug("[message.embed] Server is online")
        except:
            pass

        embed = self.standardEmbed(
            title=f"{isOnline} {data['host']['hostname']}",
            description=self.text.colorAnsi(data["description"]["text"]),
            color=self.GREEN if isOnline == "🟢" else self.RED,
        )

        # set the footer to say the index, pipeline, and total servers
        embed.set_footer(
            f"Showing {index + 1} of {total_servers} servers in: {pipeline[0]}",
        )
        embed.timestamp = self.text.timeNow()

        # get the server icon
        if "favicon" in data and isOnline == "🟢":
            bits = data["favicon"].split(",")[1]
            with open("favicon.png", "wb") as f:
                f.write(base64.b64decode(bits))
            _file = interactions.File(
                file_name="favicon.png",
            )
        else:
            _file = None

        if _file is not None:
            embed.set_thumbnail(url="attachment://favicon.png")
            self.logger.debug("[message.embed] Server has an icon")

        # add the version
        embed.add_field(
            name="Version",
            value=f"{data['version']['name']} ({data['version']['protocol']})",
            inline=True,
        )

        # add the player count
        embed.add_field(
            name="Players",
            value=f"{data['players']['online']}/{data['players']['max']}",
            inline=True,
        )

        # is cracked
        embed.add_field(
            name="Cracked",
            value="Yes" if data["cracked"] else "No",
            inline=True,
        )

        # last online
        embed.add_field(
            name="Time since last scan",
            value=self.text.timeAgo(data["last_online"]),
            inline=False,
        )

        return {
            "embed": embed,
            "components": self.buttons(
                total_servers > 1,
                index > 0,
                "sample" in data,
            ),
        }

    def standardEmbed(
        self,
        title: str,
        description: str,
        color: int,
    ) -> interactions.Embed:
        """Return a standard embed

        Args:
            title (str): The title of the embed
            description (str): The description of the embed
            color (int): The color of the embed (
                RED: error
                GREEN: success
                YELLOW: warning
                BLUE: info
                PINK: offline
            )

        Returns:
            interactions.Embed: The embed
        """
        return interactions.Embed(
            title=title,
            description=description,
            color=color,
        )
