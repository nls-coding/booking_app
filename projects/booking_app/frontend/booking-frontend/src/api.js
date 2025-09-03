const API = "http://localhost:8000/api";

export const getPlansBySpot = async (spotId) =>
  (await fetch(`${API}/booking_spots/${spotId}/plans`)).json();

export const listSpots = async () =>
  (await fetch(`${API}/booking_spots`)).json();

export const listReservationsByDate = async (date) =>
  (await fetch(`${API}/reservations?date=${date}`)).json();

export const createReservation = async (payload) =>
  (await fetch(`${API}/reservations`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  })).json();

export const listUsers = async () =>
  (await fetch(`${API}/users`)).json();
