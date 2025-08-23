--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9
-- Dumped by pg_dump version 16.9

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: order_items; Type: TABLE; Schema: public; Owner: sri
--

CREATE TABLE public.order_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    price_at_purchase numeric(10,2) NOT NULL,
    product_name character varying(255),
    image_url character varying(255)
);


ALTER TABLE public.order_items OWNER TO sri;

--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: sri
--

CREATE SEQUENCE public.order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_items_id_seq OWNER TO sri;

--
-- Name: order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sri
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: sri
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    order_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    total_amount numeric(10,2) NOT NULL,
    status character varying(50) DEFAULT 'Pending'::character varying,
    user_email character varying(255),
    razorpay_order_id character varying(255) NOT NULL,
    razorpay_payment_id character varying(255) NOT NULL
);


ALTER TABLE public.orders OWNER TO sri;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: sri
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO sri;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sri
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: sri
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    category text,
    price numeric,
    rating numeric,
    image_url text,
    created_by character varying(255)
);


ALTER TABLE public.products OWNER TO sri;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: sri
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO sri;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sri
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: sri
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    product_id integer NOT NULL,
    user_id integer,
    username character varying(255) NOT NULL,
    rating integer,
    comment text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO sri;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: sri
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO sri;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sri
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: sri
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    password text NOT NULL,
    address text,
    phone character varying(20)
);


ALTER TABLE public.users OWNER TO sri;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: sri
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO sri;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sri
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: order_items id; Type: DEFAULT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: sri
--

COPY public.order_items (id, order_id, product_id, quantity, price_at_purchase, product_name, image_url) FROM stdin;
1	4	7	1	1.00	Green Wall Desk	img/Products/Screenshot_2025-08-16_at_10.48.06_PM.png
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: sri
--

COPY public.orders (id, user_id, order_date, total_amount, status, user_email, razorpay_order_id, razorpay_payment_id) FROM stdin;
4	9	2025-08-23 18:57:13.961535	1.00	Completed	sri@gmail.com	order_R8sn2pwhlyf26d	pay_R8snF3eP1pNFcA
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: sri
--

COPY public.products (id, name, description, category, price, rating, image_url, created_by) FROM stdin;
8	GlowSpace	A sleek minimalist desk with warm ambient lighting – where work meets inspiration	executive	55000.0	4.0	img/Products/Screenshot_2025-08-16_at_10.53.22_PM.png	sri@gmail.com
9	Scandi Minimal	Balanced simplicity with warm wood, neutral tones, and clutter-free design for a calming work vibe.	minimalist	35000.0	5.0	img/Products/f996ebea3a130d8dd1bb5b2f1f938455.jpg	sri@gmail.com
10	Neo Ergonomic Desk	Clean, modern workspace with an ergonomic chair, sleek desk, and fresh greenery for comfort and focus.	Ergonomic	58000.0	5.0	img/Products/DSC06916.jpg	sri@gmail.com
11	Dual Harmony	A stylish side-by-side desk setup designed for couples who work, create, or study together. This shared workspace balances productivity with harmony.	couple	99000.0	5.0	img/Products/dualdesks_1.jpg	sri@gmail.com
7	Green Wall Desk	A modern desk setup blending greenery with minimal design — perfect for focus and calm	ergonomic	1	4.0	img/Products/Screenshot_2025-08-16_at_10.48.06_PM.png	sri@gmail.com
12	Neon Dreamscape	The vibrant blue illumination and geometric wall panels create a dynamic and stylish space, ideal for both high-energy gaming and creative endeavors.	gaming	75000.0	4.0	img/Products/Screenshot_2025-08-19_at_4.35.56_AM.png	srichityala501@gmail.com
13	Serene Balcony Nook	Designed for tranquility and concentration, this balcony workspace combines natural light and simple decor to offer a peaceful retreat for daily tasks	balcony	38000.0	5.0	img/Products/balcony.jpg	srichityala501@gmail.com
14	Minimalist Balcony	Featuring clean lines, neutral tones, and essential elements, this design maximizes a compact balcony to create an efficient and aesthetically pleasing remote work	balcony	32000.0	5.0	img/Products/972b8295b1e88af3a3389a606f900d78.jpg	srichityala501@gmail.com
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: sri
--

COPY public.reviews (id, product_id, user_id, username, rating, comment, created_at) FROM stdin;
1	7	\N	sri@gmail.com	5	Very comfortable 	2025-08-16 17:41:13.894303
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: sri
--

COPY public.users (id, name, email, password, address, phone) FROM stdin;
9	sri	sri@gmail.com	sri	\N	\N
10	Syed Ahmed	syed.ahmed8801302@gmail.com	aTNkZUoq	\N	\N
11	syed	syed@gmail.com	syed	\N	\N
12	Home	sri.chityala504@gmail.com		\N	\N
13	Sri ch	sri.chityala500@gmail.com	hello	\N	\N
14	chityala srikanth	srichityala501@gmail.com		\N	\N
\.


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sri
--

SELECT pg_catalog.setval('public.order_items_id_seq', 1, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sri
--

SELECT pg_catalog.setval('public.orders_id_seq', 4, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sri
--

SELECT pg_catalog.setval('public.products_id_seq', 14, true);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sri
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sri
--

SELECT pg_catalog.setval('public.users_id_seq', 14, true);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: orders orders_razorpay_order_id_key; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_razorpay_order_id_key UNIQUE (razorpay_order_id);


--
-- Name: orders orders_razorpay_payment_id_key; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_razorpay_payment_id_key UNIQUE (razorpay_payment_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE RESTRICT;


--
-- Name: orders orders_user_email_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_email_fkey FOREIGN KEY (user_email) REFERENCES public.users(email);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sri
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

