export type Role = "customer" | "admin";

export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  role: Role;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: string;
  image_url: string | null;
  stock: number;
  is_active: boolean;
}

export type OrderStatus = "pending_payment" | "paid" | "failed" | "cancelled";

export interface OrderItem {
  product_id: number;
  product_name: string;
  unit_price: string;
  quantity: number;
}

export interface Order {
  id: number;
  status: OrderStatus;
  total_amount: string;
  created_at: string;
  user_email: string;
  items: OrderItem[];
}

export interface CartLine {
  product: Product;
  quantity: number;
}
