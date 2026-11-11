export class ParkingResultsError extends Error {
  constructor(message) {
    super(message);
    this.name = "ParkingResultsError";
  }
}
