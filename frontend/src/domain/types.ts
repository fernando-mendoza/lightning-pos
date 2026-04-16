export interface Product {
  id: string;
  name: string;
  price_mxn: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SaleItem {
  id: string;
  sale_id: string;
  product_id: string;
  product_name: string;
  price_mxn: number;
  quantity: number;
  subtotal_mxn: number;
}

export interface Sale {
  id: string;
  total_mxn: number;
  total_sats: number;
  exchange_rate: number;
  payment_hash: string;
  bolt11: string;
  status: "pending" | "paid" | "expired";
  created_at: string;
  paid_at: string | null;
  items: SaleItem[];
}

export interface ExchangeRate {
  mxn_per_btc: number;
  sats_per_mxn: number;
  fetched_at: number;
  source: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}
