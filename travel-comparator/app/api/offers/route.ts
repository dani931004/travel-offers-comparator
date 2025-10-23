import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const dbPath = '/home/dani/Desktop/Organizer/travel_offers.db';
const db = new Database(dbPath);

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const destination = searchParams.get('destination');
  const minPrice = searchParams.get('min_price');
  const maxPrice = searchParams.get('max_price');
  const startDate = searchParams.get('start_date');
  const endDate = searchParams.get('end_date');

  let query = 'SELECT * FROM offers WHERE 1=1';
  const params: any[] = [];

  if (destination) {
    query += ' AND destination LIKE ?';
    params.push(`%${destination}%`);
  }
  if (minPrice) {
    query += ' AND price_eur >= ?';
    params.push(parseFloat(minPrice));
  }
  if (maxPrice) {
    query += ' AND price_eur <= ?';
    params.push(parseFloat(maxPrice));
  }
  if (startDate) {
    query += ' AND dates_start >= ?';
    params.push(startDate);
  }
  if (endDate) {
    query += ' AND dates_end <= ?';
    params.push(endDate);
  }

  query += ' ORDER BY price_eur ASC';

  try {
    const stmt = db.prepare(query);
    const offers = stmt.all(...params);
    return NextResponse.json(offers);
  } catch (error) {
    return NextResponse.json({ error: 'Database error' }, { status: 500 });
  }
}