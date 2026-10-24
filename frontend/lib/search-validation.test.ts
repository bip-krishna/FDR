import { describe, expect, it } from "vitest";
import { validateSearch, type SearchValidationInput } from "./search-validation";

const today = "2026-10-24";

function validInput(overrides: Partial<SearchValidationInput> = {}): SearchValidationInput {
  return {
    origin: "Delhi",
    destination: "Mumbai",
    departureDate: "2026-10-26",
    returnDate: "2026-10-30",
    tripType: "round",
    budget: "",
    maxDuration: "",
    ...overrides,
  };
}

describe("validateSearch", () => {
  it("requires both locations and a departure date", () => {
    const errors = validateSearch(validInput({ origin: "", destination: " ", departureDate: "", returnDate: "" }), today);
    expect(errors.origin).toBe("Enter a city or location.");
    expect(errors.destination).toBe("Enter a city or location.");
    expect(errors.date).toBe("Choose a departure date.");
    expect(errors.returnDate).toBe("Choose a return date.");
  });

  it("rejects an origin repeated as the destination, ignoring case", () => {
    const errors = validateSearch(validInput({ origin: " New Delhi ", destination: "new delhi" }), today);
    expect(errors.destination).toBe("Choose a destination different from your origin.");
  });

  it("rejects past departure dates", () => {
    const errors = validateSearch(validInput({ departureDate: "2026-10-23" }), today);
    expect(errors.date).toBe("Departure date cannot be in the past.");
  });

  it("rejects a return date before departure", () => {
    const errors = validateSearch(validInput({ departureDate: "2026-10-27", returnDate: "2026-10-26" }), today);
    expect(errors.returnDate).toBe("Return must be on or after departure.");
  });

  it("accepts a valid one-way trip without a return date", () => {
    expect(validateSearch(validInput({ tripType: "one-way", returnDate: "" }), today)).toEqual({});
  });

  it("accepts a valid round trip", () => {
    expect(validateSearch(validInput(), today)).toEqual({});
  });

  it("rejects negative or non-numeric budgets", () => {
    expect(validateSearch(validInput({ budget: "-1" }), today).budget).toBe("Enter a valid budget of zero or more.");
    expect(validateSearch(validInput({ budget: "not-a-number" }), today).budget).toBe("Enter a valid budget of zero or more.");
  });

  it("limits journey duration to 1–96 hours", () => {
    expect(validateSearch(validInput({ maxDuration: "0" }), today).maxDuration).toBeTruthy();
    expect(validateSearch(validInput({ maxDuration: "97" }), today).maxDuration).toBeTruthy();
    expect(validateSearch(validInput({ maxDuration: "96" }), today).maxDuration).toBeUndefined();
  });
});
