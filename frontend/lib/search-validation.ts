export type TripType = "round" | "one-way";

export type SearchValidationErrors = Partial<
  Record<"origin" | "destination" | "date" | "returnDate" | "budget" | "maxDuration", string>
>;

export type SearchValidationInput = {
  origin: string;
  destination: string;
  departureDate: string;
  returnDate: string;
  tripType: TripType;
  budget: string;
  maxDuration: string;
};

export function validateSearch(input: SearchValidationInput, today: string): SearchValidationErrors {
  const errors: SearchValidationErrors = {};
  const origin = input.origin.trim();
  const destination = input.destination.trim();

  if (origin.length < 2) errors.origin = "Enter a city or location.";
  if (destination.length < 2) errors.destination = "Enter a city or location.";
  if (origin && destination && origin.toLowerCase() === destination.toLowerCase()) {
    errors.destination = "Choose a destination different from your origin.";
  }

  if (!input.departureDate) errors.date = "Choose a departure date.";
  else if (input.departureDate < today) errors.date = "Departure date cannot be in the past.";

  if (input.tripType === "round") {
    if (!input.returnDate) errors.returnDate = "Choose a return date.";
    else if (input.returnDate < input.departureDate) errors.returnDate = "Return must be on or after departure.";
  }

  if (input.budget && (!Number.isFinite(Number(input.budget)) || Number(input.budget) < 0)) {
    errors.budget = "Enter a valid budget of zero or more.";
  }

  if (input.maxDuration && (!Number.isFinite(Number(input.maxDuration)) || Number(input.maxDuration) < 1 || Number(input.maxDuration) > 96)) {
    errors.maxDuration = "Enter a duration between 1 and 96 hours.";
  }

  return errors;
}
