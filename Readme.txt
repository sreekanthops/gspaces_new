CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    price NUMERIC,
    rating NUMERIC,
    image_url TEXT
);


gspaces=> select * from products;
 id | name | description | category  | price | rating |         image_url       
   | created_by 
