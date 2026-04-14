from typing import Dict, Optional
from pydantic import BaseModel

from .layout import Platform, AnchorSide, ConfigDefaults

class ScaledAnchorPoints(BaseModel):
    deck_left_pos: int
    deck_right_pos: int
    mixer_left_pos: int
    mixer_right_pos: int
    y_offset: int

    def _anchor_to(self, left_pos, right_pos, property_config):
        result = [[0, 0], [0, 0]]

        left_x = property_config.bb[0][0]
        if property_config.left_anchor == AnchorSide.LEFT:
            result[0][0] = left_pos + left_x
        elif property_config.left_anchor == AnchorSide.RIGHT:
            result[0][0] = right_pos + left_x

        result[0][1] = (property_config.bb[0][1] + self.y_offset)

        right_x = property_config.bb[1][0]
        if property_config.right_anchor == AnchorSide.LEFT:
            result[1][0] = left_pos + right_x
        elif property_config.right_anchor == AnchorSide.RIGHT:
            result[1][0] = right_pos + right_x

        result[1][1] = (property_config.bb[1][1] + self.y_offset)

        return result

    def anchor_to_deck(self, property_config):
        return self._anchor_to(self.deck_left_pos, self.deck_right_pos, property_config)

    def anchor_to_mixer(self, property_config):
        return self._anchor_to(self.mixer_left_pos, self.mixer_right_pos, property_config)

class Scaler(BaseModel):
    config_defaults: ConfigDefaults

    current_width: int
    current_height: int
    platform: Platform

    @property
    def y_offset(self):
        if self.platform == Platform.WINDOWS:
            return 0
        elif self.platform == Platform.MAC:
            return -45
        else:
            raise ValueError(f"Unkown Y offset for platform: {self.platform}")

    @property
    def x_scaling_factor(self):
        return (self.current_width - self.config_defaults.mixer_width) / (self.config_defaults.screen_width - self.config_defaults.mixer_width)

    @property
    def deck_width(self):
        return self.scaling_factor * self.config_defaults.deck_width

    @property
    def mixer_x_pos(self):
        return self.deck_width

    def get_deck_x_pos(self, deck_num):
        is_left_deck = (deck_num % 2 == 0)
        if is_left_deck:
            return 0

        return self.deck_width + self.config_defaults.mixer_width

    def get_scaled_anchor_points(self, deck_num):
        deck_left_pos = self.get_deck_x_pos(deck_num)
        deck_right_pos = deck_left_pos + self.deck_width
        mixer_left_pos = self.mixer_x_pos
        mixer_right_pos = mixer_left_pos + self.config_defaults.mixer_width

        return ScaledAnchorPoints(
            deck_left_pos = int(deck_left_pos),
            deck_right_pos = int(deck_right_pos),
            mixer_left_pos = int(mixer_left_pos),
            mixer_right_pos = int(mixer_right_pos)
        )

class ScalerFactory(BaseModel):
    config_defaults: ConfigDefaults
    _scaler_map: Dict[int, Dict[int, Scaler]]

    def get_scaler(self, current_width, current_height, platform):
        if current_width not in self._scaler_map:
            self._scaler_map[current_width] = {}

        if current_height not in self._scaler_map[current_width]:
            self._scaler_map[current_width][current_height] = Scaler(
                self.config_defaults,
                current_width,
                current_height,
                platform
            )

        return self._scaler_map[current_width][current_height]