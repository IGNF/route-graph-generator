--
-- PostgreSQL database dump
--

-- Dumped from database version 14.7 (Ubuntu 14.7-1.pgdg22.04+1)
-- Dumped by pg_dump version 15.2 (Ubuntu 15.2-1.pgdg22.04+1)

-- Started on 2023-02-15 16:17:18 CET

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 225 (class 1259 OID 2521477)
-- Name: non_communication; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE non_communication (
    fid bigint,
    geom public.geometry(Point,2154),
    cleabs character varying(24),
    date_creation timestamp without time zone,
    date_modification timestamp without time zone,
    date_d_apparition date,
    date_de_confirmation date,
    lien_vers_troncon_entree character varying(24),
    liens_vers_troncon_sortie character varying
);


--
-- TOC entry 4615 (class 0 OID 2521477)
-- Dependencies: 225
-- Data for Name: non_communication; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO non_communication VALUES (168, '01010000206A0800009A999999604A2B419A9999B965D35741', 'NON_COMM0000000040688510', '2006-11-22 12:22:15.461', NULL, NULL, NULL, 'TRONROUT0000000040969830', 'TRONROUT0000000040969807');
INSERT INTO non_communication VALUES (172, '01010000206A08000000000000FC4E2B41000000A0EED25741', 'NON_COMM0000000040688505', '2006-11-22 12:22:15.461', NULL, NULL, NULL, 'TRONROUT0000000040969480', 'TRONROUT0000000040969520');
INSERT INTO non_communication VALUES (173, '01010000206A08000000000000FC4E2B41000000A0EED25741', 'NON_COMM0000000040688503', '2006-11-22 12:22:15.461', NULL, NULL, NULL, 'TRONROUT0000000040969520', 'TRONROUT0000000040972944');


-- Completed on 2023-02-15 16:17:18 CET

--
-- PostgreSQL database dump complete
--

