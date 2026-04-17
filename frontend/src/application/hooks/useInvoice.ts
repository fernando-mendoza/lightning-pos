import { useState } from "react";
import { api } from "../../infrastructure/api";
import type { CartItem } from "../../domain/types";

interface InvoiceData {
  sale_id: string;
  payment_hash: string;
  bolt11: string;
  total_mxn: number;
  total_sats: number;
  exchange_rate: number;
  expires_at: number;
  tip_mxn: number;
  discount_mxn: number;
}

interface CheckoutOptions {
  tipMxn?: number;
  discountMxn?: number;
}

export function useInvoice() {
  const [invoice, setInvoice] = useState<InvoiceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createInvoice = async (
    items: CartItem[],
    options: CheckoutOptions = {}
  ) => {
    setLoading(true);
    setError(null);
    try {
      const payload = items.map((i) => ({
        product_id: i.product.id,
        product_name: i.product.name,
        price_mxn: i.product.price_mxn,
        quantity: i.quantity,
      }));
      const data = await api.invoices.create(payload, options);
      setInvoice(data);
      return data;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error creating invoice";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setInvoice(null);
    setError(null);
  };

  return { invoice, loading, error, createInvoice, reset };
}
