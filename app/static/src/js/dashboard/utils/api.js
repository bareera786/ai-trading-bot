/**
 * API utilities for the dashboard
 */

import { fetchJson } from './network.js';

export async function apiRequest(url, options = {}) {
  try {
    const response = await fetchJson(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    return response;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}