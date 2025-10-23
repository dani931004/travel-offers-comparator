import React from 'react';

interface Offer {
  id: string;
  agency: string;
  title: string;
  destination: string;
  price_eur: number;
  dates_start: string;
  dates_end: string;
  duration_days: number;
  program_info: string;
  price_includes: string[];
  price_excludes: string[];
  hotel_titles: string[];
  booking_conditions: string;
  link: string;
  scraped_at: string;
}

interface OfferCardProps {
  offer: Offer;
}

const OfferCard: React.FC<OfferCardProps> = ({ offer }) => {
  return (
    <div key={offer.id} className="bg-white p-4 rounded-lg shadow-md border border-gray-300">
      <h3 className="text-lg font-semibold mb-2">{offer.title}</h3>
      <p className="text-gray-600 mb-1">Agency: {offer.agency}</p>
      <p className="text-gray-600 mb-1">Destination: {offer.destination}</p>
      <p className="text-green-600 font-bold mb-1">Price: {offer.price_eur} EUR</p>
      <p className="text-gray-600 mb-1">Dates: {offer.dates_start || 'N/A'} - {offer.dates_end || 'N/A'}</p>
      <a href={offer.link} target="_blank" className="text-blue-600 hover:underline">View Details</a>
    </div>
  );
};

export default OfferCard;