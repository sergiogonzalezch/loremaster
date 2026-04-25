import { describe, it, expect } from "vitest";
import {
  ENTITY_CATEGORY_MAP,
  ENTITY_TYPE_BADGE,
  ENTITY_TYPE_LABELS,
  CATEGORY_LABELS,
  MAX_PENDING_CONTENTS,
} from "../utils/constants";
import type { EntityType, ContentCategory } from "../utils/enums";

const ENTITY_TYPES: EntityType[] = [
  "character",
  "creature",
  "location",
  "faction",
  "item",
];
const CONTENT_CATEGORIES: ContentCategory[] = [
  "backstory",
  "extended_description",
  "scene",
  "chapter",
];

describe("ENTITY_CATEGORY_MAP", () => {
  it("cubre los 5 tipos de entidad", () => {
    for (const type of ENTITY_TYPES) {
      expect(ENTITY_CATEGORY_MAP).toHaveProperty(type);
    }
  });

  it("character tiene 4 categorías", () => {
    expect(ENTITY_CATEGORY_MAP.character).toHaveLength(4);
  });

  it("location tiene 2 categorías (la más restrictiva)", () => {
    expect(ENTITY_CATEGORY_MAP.location).toHaveLength(2);
  });

  it("item no incluye scene ni chapter", () => {
    expect(ENTITY_CATEGORY_MAP.item).not.toContain("scene");
    expect(ENTITY_CATEGORY_MAP.item).not.toContain("chapter");
  });
});

describe("ENTITY_TYPE_BADGE", () => {
  it("cubre los 5 tipos con un string de variante Bootstrap", () => {
    for (const type of ENTITY_TYPES) {
      expect(typeof ENTITY_TYPE_BADGE[type]).toBe("string");
      expect(ENTITY_TYPE_BADGE[type].length).toBeGreaterThan(0);
    }
  });
});

describe("ENTITY_TYPE_LABELS", () => {
  it("cubre los 5 tipos con etiquetas en español", () => {
    for (const type of ENTITY_TYPES) {
      expect(typeof ENTITY_TYPE_LABELS[type]).toBe("string");
    }
  });
});

describe("CATEGORY_LABELS", () => {
  it("cubre las 4 categorías con etiquetas en español", () => {
    for (const cat of CONTENT_CATEGORIES) {
      expect(typeof CATEGORY_LABELS[cat]).toBe("string");
    }
  });
});

describe("MAX_PENDING_CONTENTS", () => {
  it("es 5", () => {
    expect(MAX_PENDING_CONTENTS).toBe(5);
  });
});
