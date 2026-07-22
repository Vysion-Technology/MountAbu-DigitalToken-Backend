--
-- PostgreSQL database dump
--

\restrict m7wxAxJGF6SYDYgdOwWtPHbWIwA38wsB7wiQp450VnkQ7sQlzMWhgnKHZQWkbUO

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

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

ALTER TABLE IF EXISTS ONLY public.wards DROP CONSTRAINT IF EXISTS wards_created_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.tenders DROP CONSTRAINT IF EXISTS tenders_department_id_fkey;
ALTER TABLE IF EXISTS ONLY public.tenders DROP CONSTRAINT IF EXISTS tenders_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_created_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.notices DROP CONSTRAINT IF EXISTS notices_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.materials DROP CONSTRAINT IF EXISTS materials_created_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.leaders DROP CONSTRAINT IF EXISTS leaders_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.events DROP CONSTRAINT IF EXISTS events_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.downloads DROP CONSTRAINT IF EXISTS downloads_uploaded_by_fkey;
ALTER TABLE IF EXISTS ONLY public.downloads DROP CONSTRAINT IF EXISTS downloads_department_id_fkey;
ALTER TABLE IF EXISTS ONLY public.departments DROP CONSTRAINT IF EXISTS departments_created_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.contact_diaries DROP CONSTRAINT IF EXISTS contact_diaries_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.complaint_categories DROP CONSTRAINT IF EXISTS complaint_categories_department_id_fkey;
ALTER TABLE IF EXISTS ONLY public.complaint_categories DROP CONSTRAINT IF EXISTS complaint_categories_created_by_id_fkey;
ALTER TABLE IF EXISTS ONLY public.city_profiles DROP CONSTRAINT IF EXISTS city_profiles_created_by_id_fkey;
DROP INDEX IF EXISTS public.ix_wards_name;
DROP INDEX IF EXISTS public.ix_wards_id;
DROP INDEX IF EXISTS public.ix_wards_code;
DROP INDEX IF EXISTS public.ix_users_username;
DROP INDEX IF EXISTS public.ix_users_role;
DROP INDEX IF EXISTS public.ix_users_password;
DROP INDEX IF EXISTS public.ix_users_name;
DROP INDEX IF EXISTS public.ix_users_mobile;
DROP INDEX IF EXISTS public.ix_users_id;
DROP INDEX IF EXISTS public.ix_tenders_title;
DROP INDEX IF EXISTS public.ix_tenders_tender_type;
DROP INDEX IF EXISTS public.ix_tenders_status;
DROP INDEX IF EXISTS public.ix_tenders_id;
DROP INDEX IF EXISTS public.ix_tenders_department_id;
DROP INDEX IF EXISTS public.ix_roles_name;
DROP INDEX IF EXISTS public.ix_roles_id;
DROP INDEX IF EXISTS public.ix_roles_code;
DROP INDEX IF EXISTS public.ix_notices_visibility;
DROP INDEX IF EXISTS public.ix_notices_title;
DROP INDEX IF EXISTS public.ix_notices_status;
DROP INDEX IF EXISTS public.ix_notices_notice_type;
DROP INDEX IF EXISTS public.ix_notices_id;
DROP INDEX IF EXISTS public.ix_materials_unit;
DROP INDEX IF EXISTS public.ix_materials_name;
DROP INDEX IF EXISTS public.ix_materials_id;
DROP INDEX IF EXISTS public.ix_leaders_status;
DROP INDEX IF EXISTS public.ix_leaders_name;
DROP INDEX IF EXISTS public.ix_leaders_id;
DROP INDEX IF EXISTS public.ix_events_title;
DROP INDEX IF EXISTS public.ix_events_status;
DROP INDEX IF EXISTS public.ix_events_id;
DROP INDEX IF EXISTS public.ix_events_event_type;
DROP INDEX IF EXISTS public.ix_downloads_status;
DROP INDEX IF EXISTS public.ix_downloads_id;
DROP INDEX IF EXISTS public.ix_downloads_document_type;
DROP INDEX IF EXISTS public.ix_downloads_document_title;
DROP INDEX IF EXISTS public.ix_downloads_department_id;
DROP INDEX IF EXISTS public.ix_departments_name;
DROP INDEX IF EXISTS public.ix_departments_id;
DROP INDEX IF EXISTS public.ix_departments_code;
DROP INDEX IF EXISTS public.ix_contact_diaries_status;
DROP INDEX IF EXISTS public.ix_contact_diaries_office_department;
DROP INDEX IF EXISTS public.ix_contact_diaries_id;
DROP INDEX IF EXISTS public.ix_contact_diaries_designation;
DROP INDEX IF EXISTS public.ix_contact_diaries_contact_person;
DROP INDEX IF EXISTS public.ix_complaint_categories_name;
DROP INDEX IF EXISTS public.ix_complaint_categories_id;
DROP INDEX IF EXISTS public.ix_city_profiles_id;
ALTER TABLE IF EXISTS ONLY public.wards DROP CONSTRAINT IF EXISTS wards_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.tenders DROP CONSTRAINT IF EXISTS tenders_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_pkey;
ALTER TABLE IF EXISTS ONLY public.notices DROP CONSTRAINT IF EXISTS notices_pkey;
ALTER TABLE IF EXISTS ONLY public.materials DROP CONSTRAINT IF EXISTS materials_pkey;
ALTER TABLE IF EXISTS ONLY public.leaders DROP CONSTRAINT IF EXISTS leaders_pkey;
ALTER TABLE IF EXISTS ONLY public.events DROP CONSTRAINT IF EXISTS events_pkey;
ALTER TABLE IF EXISTS ONLY public.downloads DROP CONSTRAINT IF EXISTS downloads_pkey;
ALTER TABLE IF EXISTS ONLY public.departments DROP CONSTRAINT IF EXISTS departments_pkey;
ALTER TABLE IF EXISTS ONLY public.contact_diaries DROP CONSTRAINT IF EXISTS contact_diaries_pkey;
ALTER TABLE IF EXISTS ONLY public.complaint_categories DROP CONSTRAINT IF EXISTS complaint_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.city_profiles DROP CONSTRAINT IF EXISTS city_profiles_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.wards ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.tenders ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.roles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.notices ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.materials ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.leaders ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.events ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.downloads ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.departments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.contact_diaries ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.complaint_categories ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.city_profiles ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.wards_id_seq;
DROP TABLE IF EXISTS public.wards;
DROP SEQUENCE IF EXISTS public.vehicle_materials_id_seq;
DROP SEQUENCE IF EXISTS public.vehicle_entries_id_seq;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.tenders_id_seq;
DROP TABLE IF EXISTS public.tenders;
DROP SEQUENCE IF EXISTS public.roles_id_seq;
DROP TABLE IF EXISTS public.roles;
DROP SEQUENCE IF EXISTS public.notices_id_seq;
DROP TABLE IF EXISTS public.notices;
DROP SEQUENCE IF EXISTS public.materials_id_seq;
DROP TABLE IF EXISTS public.materials;
DROP SEQUENCE IF EXISTS public.leaders_id_seq;
DROP TABLE IF EXISTS public.leaders;
DROP SEQUENCE IF EXISTS public.inspection_reports_id_seq;
DROP SEQUENCE IF EXISTS public.events_id_seq;
DROP TABLE IF EXISTS public.events;
DROP SEQUENCE IF EXISTS public.downloads_id_seq;
DROP TABLE IF EXISTS public.downloads;
DROP SEQUENCE IF EXISTS public.departments_id_seq;
DROP TABLE IF EXISTS public.departments;
DROP SEQUENCE IF EXISTS public.contact_diaries_id_seq;
DROP TABLE IF EXISTS public.contact_diaries;
DROP SEQUENCE IF EXISTS public.complaints_id_seq;
DROP SEQUENCE IF EXISTS public.complaint_media_id_seq;
DROP SEQUENCE IF EXISTS public.complaint_comments_id_seq;
DROP SEQUENCE IF EXISTS public.complaint_categories_id_seq;
DROP TABLE IF EXISTS public.complaint_categories;
DROP SEQUENCE IF EXISTS public.city_profiles_id_seq;
DROP TABLE IF EXISTS public.city_profiles;
DROP SEQUENCE IF EXISTS public.audit_logs_id_seq;
DROP SEQUENCE IF EXISTS public.applications_id_seq;
DROP SEQUENCE IF EXISTS public.application_phases_id_seq;
DROP SEQUENCE IF EXISTS public.application_phase_materials_id_seq;
DROP SEQUENCE IF EXISTS public.application_materials_id_seq;
DROP SEQUENCE IF EXISTS public.application_documents_id_seq;
DROP SEQUENCE IF EXISTS public.application_comments_id_seq;
DROP SEQUENCE IF EXISTS public.application_approvals_id_seq;
DROP SEQUENCE IF EXISTS public.application_action_logs_id_seq;
DROP TABLE IF EXISTS public.alembic_version;
DROP SEQUENCE IF EXISTS public.active_user_otps_id_seq;
DROP TYPE IF EXISTS public.workflowaction;
DROP TYPE IF EXISTS public.userrole;
DROP TYPE IF EXISTS public.tenderstatus;
DROP TYPE IF EXISTS public.propertyusagetype;
DROP TYPE IF EXISTS public.noticevisibility;
DROP TYPE IF EXISTS public.noticestatus;
DROP TYPE IF EXISTS public.leaderstatus;
DROP TYPE IF EXISTS public.eventstatus;
DROP TYPE IF EXISTS public.downloadstatus;
DROP TYPE IF EXISTS public.complaintstatus;
DROP TYPE IF EXISTS public.commenttype;
DROP TYPE IF EXISTS public.auditaction;
DROP TYPE IF EXISTS public.applicationtype;
DROP TYPE IF EXISTS public.applicationstatus;
DROP TYPE IF EXISTS public.applicationphasestatus;
DROP TYPE IF EXISTS public.applicationdocumenttype;
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS pg_trgm;
--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: applicationdocumenttype; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.applicationdocumenttype AS ENUM (
    'APPLICATION',
    'INSPECTION',
    'OTHER',
    'AADHAAR',
    'APPLICANT_PHOTO',
    'OWNERSHIP_DOCUMENTS',
    'PERMISSION_DOCUMENTS',
    'PROPERTY_PHOTOS',
    'SUPPORTING_DOCUMENTS',
    'SITE_INSPECTION',
    'GEO_TAGGED_PHOTO'
);


ALTER TYPE public.applicationdocumenttype OWNER TO etoken_user;

--
-- Name: applicationphasestatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.applicationphasestatus AS ENUM (
    'PENDING',
    'APPROVED',
    'WITHHELD',
    'REJECTED',
    'TERMINATED',
    'IN_PROGRESS',
    'COMPLETED',
    'ACTIVE'
);


ALTER TYPE public.applicationphasestatus OWNER TO etoken_user;

--
-- Name: applicationstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.applicationstatus AS ENUM (
    'PENDING',
    'SUBMITTED',
    'APPROVED',
    'WITHHELD',
    'OBJECTED',
    'REJECTED',
    'FORWARDED',
    'TOKEN_GENERATED'
);


ALTER TYPE public.applicationstatus OWNER TO etoken_user;

--
-- Name: applicationtype; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.applicationtype AS ENUM (
    'NEW',
    'RENOVATION'
);


ALTER TYPE public.applicationtype OWNER TO etoken_user;

--
-- Name: auditaction; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.auditaction AS ENUM (
    'CHANGED',
    'CREATED',
    'VIEWED'
);


ALTER TYPE public.auditaction OWNER TO etoken_user;

--
-- Name: commenttype; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.commenttype AS ENUM (
    'GENERAL',
    'DEPT_REVIEW',
    'OBJECTION_RESPONSE',
    'INSPECTION_REMARK',
    'OBJECTION_COMMENT'
);


ALTER TYPE public.commenttype OWNER TO etoken_user;

--
-- Name: complaintstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.complaintstatus AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'RESOLVED',
    'WITHHELD',
    'REJECTED'
);


ALTER TYPE public.complaintstatus OWNER TO etoken_user;

--
-- Name: downloadstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.downloadstatus AS ENUM (
    'ACTIVE',
    'INACTIVE'
);


ALTER TYPE public.downloadstatus OWNER TO etoken_user;

--
-- Name: eventstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.eventstatus AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'CANCELLED',
    'CLOSED'
);


ALTER TYPE public.eventstatus OWNER TO etoken_user;

--
-- Name: leaderstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.leaderstatus AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'INACTIVE'
);


ALTER TYPE public.leaderstatus OWNER TO etoken_user;

--
-- Name: noticestatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.noticestatus AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'INACTIVE'
);


ALTER TYPE public.noticestatus OWNER TO etoken_user;

--
-- Name: noticevisibility; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.noticevisibility AS ENUM (
    'PUBLIC',
    'INTERNAL'
);


ALTER TYPE public.noticevisibility OWNER TO etoken_user;

--
-- Name: propertyusagetype; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.propertyusagetype AS ENUM (
    'DOMESTIC',
    'COMMERCIAL',
    'HOTEL'
);


ALTER TYPE public.propertyusagetype OWNER TO etoken_user;

--
-- Name: tenderstatus; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.tenderstatus AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'CANCELLED',
    'CLOSED'
);


ALTER TYPE public.tenderstatus OWNER TO etoken_user;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.userrole AS ENUM (
    'SUPERADMIN',
    'NODAL_OFFICER',
    'COMMISSIONER',
    'CITIZEN',
    'NAKA_INCHARGE',
    'DEPT_LAND',
    'DEPT_LEGAL',
    'DEPT_ATP',
    'JEN'
);


ALTER TYPE public.userrole OWNER TO etoken_user;

--
-- Name: workflowaction; Type: TYPE; Schema: public; Owner: etoken_user
--

CREATE TYPE public.workflowaction AS ENUM (
    'APPROVE',
    'REJECT',
    'OBJECT',
    'FORWARD',
    'GENERATE_TOKENS'
);


ALTER TYPE public.workflowaction OWNER TO etoken_user;

--
-- Name: active_user_otps_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.active_user_otps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.active_user_otps_id_seq OWNER TO etoken_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO etoken_user;

--
-- Name: application_action_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_action_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_action_logs_id_seq OWNER TO etoken_user;

--
-- Name: application_approvals_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_approvals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_approvals_id_seq OWNER TO etoken_user;

--
-- Name: application_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_comments_id_seq OWNER TO etoken_user;

--
-- Name: application_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_documents_id_seq OWNER TO etoken_user;

--
-- Name: application_materials_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_materials_id_seq OWNER TO etoken_user;

--
-- Name: application_phase_materials_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_phase_materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_phase_materials_id_seq OWNER TO etoken_user;

--
-- Name: application_phases_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.application_phases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_phases_id_seq OWNER TO etoken_user;

--
-- Name: applications_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.applications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.applications_id_seq OWNER TO etoken_user;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO etoken_user;

--
-- Name: city_profiles; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.city_profiles (
    id integer NOT NULL,
    area_sq_km character varying,
    no_of_wards integer,
    ward_boundaries character varying,
    population_estimate integer,
    rental_properties_of_corporation integer,
    number_of_slums integer,
    solid_waste_per_day character varying,
    street_light_poles integer,
    employees_in_board integer,
    households_residential integer,
    households_shops_offices integer,
    households_open_plots integer,
    birth_registration_per_year integer,
    birth_certificate_per_year integer,
    created_by_id integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.city_profiles OWNER TO etoken_user;

--
-- Name: city_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.city_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.city_profiles_id_seq OWNER TO etoken_user;

--
-- Name: city_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.city_profiles_id_seq OWNED BY public.city_profiles.id;


--
-- Name: complaint_categories; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.complaint_categories (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying,
    status boolean NOT NULL,
    created_at timestamp without time zone,
    created_by_id integer,
    department_id integer
);


ALTER TABLE public.complaint_categories OWNER TO etoken_user;

--
-- Name: complaint_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.complaint_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.complaint_categories_id_seq OWNER TO etoken_user;

--
-- Name: complaint_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.complaint_categories_id_seq OWNED BY public.complaint_categories.id;


--
-- Name: complaint_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.complaint_comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.complaint_comments_id_seq OWNER TO etoken_user;

--
-- Name: complaint_media_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.complaint_media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.complaint_media_id_seq OWNER TO etoken_user;

--
-- Name: complaints_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.complaints_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.complaints_id_seq OWNER TO etoken_user;

--
-- Name: contact_diaries; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.contact_diaries (
    id integer NOT NULL,
    office_department character varying NOT NULL,
    contact_person character varying NOT NULL,
    designation character varying,
    phone_number character varying,
    email_address character varying,
    status boolean NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.contact_diaries OWNER TO etoken_user;

--
-- Name: contact_diaries_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.contact_diaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contact_diaries_id_seq OWNER TO etoken_user;

--
-- Name: contact_diaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.contact_diaries_id_seq OWNED BY public.contact_diaries.id;


--
-- Name: departments; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.departments (
    id integer NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    type character varying NOT NULL,
    status boolean NOT NULL,
    created_at timestamp without time zone,
    created_by_id integer
);


ALTER TABLE public.departments OWNER TO etoken_user;

--
-- Name: departments_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.departments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.departments_id_seq OWNER TO etoken_user;

--
-- Name: departments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.departments_id_seq OWNED BY public.departments.id;


--
-- Name: downloads; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.downloads (
    id integer NOT NULL,
    document_title character varying NOT NULL,
    document_type character varying,
    department_id integer,
    description text,
    file_path character varying NOT NULL,
    status public.downloadstatus NOT NULL,
    uploaded_by integer,
    uploaded_on timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.downloads OWNER TO etoken_user;

--
-- Name: downloads_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.downloads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.downloads_id_seq OWNER TO etoken_user;

--
-- Name: downloads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.downloads_id_seq OWNED BY public.downloads.id;


--
-- Name: events; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.events (
    id integer NOT NULL,
    title character varying NOT NULL,
    event_type character varying,
    date timestamp with time zone,
    venue character varying,
    status public.eventstatus NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.events OWNER TO etoken_user;

--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_id_seq OWNER TO etoken_user;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: inspection_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.inspection_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inspection_reports_id_seq OWNER TO etoken_user;

--
-- Name: leaders; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.leaders (
    id integer NOT NULL,
    name character varying NOT NULL,
    designation character varying,
    tenure_start timestamp with time zone,
    tenure_end timestamp with time zone,
    status public.leaderstatus NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.leaders OWNER TO etoken_user;

--
-- Name: leaders_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.leaders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaders_id_seq OWNER TO etoken_user;

--
-- Name: leaders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.leaders_id_seq OWNED BY public.leaders.id;


--
-- Name: materials; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.materials (
    id integer NOT NULL,
    name character varying NOT NULL,
    unit character varying NOT NULL,
    created_at timestamp without time zone,
    created_by_id integer
);


ALTER TABLE public.materials OWNER TO etoken_user;

--
-- Name: materials_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.materials_id_seq OWNER TO etoken_user;

--
-- Name: materials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.materials_id_seq OWNED BY public.materials.id;


--
-- Name: notices; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.notices (
    id integer NOT NULL,
    title character varying NOT NULL,
    notice_type character varying,
    published_on timestamp with time zone,
    valid_till timestamp with time zone,
    status public.noticestatus NOT NULL,
    visibility public.noticevisibility NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notices OWNER TO etoken_user;

--
-- Name: notices_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.notices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notices_id_seq OWNER TO etoken_user;

--
-- Name: notices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.notices_id_seq OWNED BY public.notices.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    permissions character varying,
    status boolean NOT NULL,
    created_at timestamp without time zone,
    created_by_id integer
);


ALTER TABLE public.roles OWNER TO etoken_user;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO etoken_user;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: tenders; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.tenders (
    id integer NOT NULL,
    title character varying NOT NULL,
    tender_type character varying,
    department_id integer,
    amount numeric(14,2),
    published_on timestamp with time zone,
    submission_deadline timestamp with time zone,
    status public.tenderstatus NOT NULL,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tenders OWNER TO etoken_user;

--
-- Name: tenders_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.tenders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tenders_id_seq OWNER TO etoken_user;

--
-- Name: tenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.tenders_id_seq OWNED BY public.tenders.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    role public.userrole NOT NULL,
    name character varying NOT NULL,
    mobile character varying(10) NOT NULL,
    username character varying,
    password character varying
);


ALTER TABLE public.users OWNER TO etoken_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO etoken_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: vehicle_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.vehicle_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_entries_id_seq OWNER TO etoken_user;

--
-- Name: vehicle_materials_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.vehicle_materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_materials_id_seq OWNER TO etoken_user;

--
-- Name: wards; Type: TABLE; Schema: public; Owner: etoken_user
--

CREATE TABLE public.wards (
    id integer NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    type character varying NOT NULL,
    description character varying,
    status boolean NOT NULL,
    created_at timestamp without time zone,
    created_by_id integer
);


ALTER TABLE public.wards OWNER TO etoken_user;

--
-- Name: wards_id_seq; Type: SEQUENCE; Schema: public; Owner: etoken_user
--

CREATE SEQUENCE public.wards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wards_id_seq OWNER TO etoken_user;

--
-- Name: wards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: etoken_user
--

ALTER SEQUENCE public.wards_id_seq OWNED BY public.wards.id;


--
-- Name: city_profiles id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.city_profiles ALTER COLUMN id SET DEFAULT nextval('public.city_profiles_id_seq'::regclass);


--
-- Name: complaint_categories id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.complaint_categories ALTER COLUMN id SET DEFAULT nextval('public.complaint_categories_id_seq'::regclass);


--
-- Name: contact_diaries id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.contact_diaries ALTER COLUMN id SET DEFAULT nextval('public.contact_diaries_id_seq'::regclass);


--
-- Name: departments id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.departments ALTER COLUMN id SET DEFAULT nextval('public.departments_id_seq'::regclass);


--
-- Name: downloads id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.downloads ALTER COLUMN id SET DEFAULT nextval('public.downloads_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: leaders id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.leaders ALTER COLUMN id SET DEFAULT nextval('public.leaders_id_seq'::regclass);


--
-- Name: materials id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.materials ALTER COLUMN id SET DEFAULT nextval('public.materials_id_seq'::regclass);


--
-- Name: notices id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.notices ALTER COLUMN id SET DEFAULT nextval('public.notices_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: tenders id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.tenders ALTER COLUMN id SET DEFAULT nextval('public.tenders_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: wards id; Type: DEFAULT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.wards ALTER COLUMN id SET DEFAULT nextval('public.wards_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.alembic_version VALUES ('cb5ecb4e393f');


--
-- Data for Name: city_profiles; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.city_profiles VALUES (1, '21.64 sq. km', 25, '21.64 sq. km', 25, 25, 0, '9.1 Tones', 150, 135, 4500, 550, 0, 800, 900, 2, '2026-02-22 10:09:55.006381');
INSERT INTO public.city_profiles VALUES (2, '21.64 sq. km', 26, '21.64 sq. km', 25, 25, 0, '9.1 Tones', 150, 135, NULL, NULL, NULL, NULL, NULL, 2, '2026-02-25 11:01:03.98308');
INSERT INTO public.city_profiles VALUES (3, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 333, NULL, NULL, NULL, NULL, 2, '2026-02-25 11:03:29.004841');
INSERT INTO public.city_profiles VALUES (4, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 333, 2, NULL, NULL, NULL, 2, '2026-02-25 16:03:25.159438');
INSERT INTO public.city_profiles VALUES (5, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 2, '2026-02-25 16:04:27.545524');
INSERT INTO public.city_profiles VALUES (6, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 222, 222, 2221, NULL, NULL, 2, '2026-02-26 16:57:56.089385');
INSERT INTO public.city_profiles VALUES (7, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 229, 222, 2221, NULL, NULL, 2, '2026-02-27 08:38:54.089242');


--
-- Data for Name: complaint_categories; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.complaint_categories VALUES (1, 'Street Light Repair', 'Issue with street lights not working or broken poles', true, NULL, NULL, 4);
INSERT INTO public.complaint_categories VALUES (2, 'Potholes & Road Repair', 'Reporting damage to city roads and potholes', true, NULL, NULL, 4);
INSERT INTO public.complaint_categories VALUES (3, 'Garbage Not Picked Up', 'Solid waste management and door-to-door collection issues', true, NULL, NULL, 7);
INSERT INTO public.complaint_categories VALUES (4, 'Stray Animal Menace', 'Issues related to stray dogs, cattle or other animals', true, NULL, NULL, 7);
INSERT INTO public.complaint_categories VALUES (5, 'Illegal Construction', 'Reporting construction without proper permits', true, NULL, NULL, 5);
INSERT INTO public.complaint_categories VALUES (6, 'Encroachment on Public Land', 'Illegal occupation of public spaces or roads', true, NULL, NULL, 5);
INSERT INTO public.complaint_categories VALUES (7, 'Drainage Blockage', 'Reporting blocked or overflowing city drains', true, NULL, NULL, 7);
INSERT INTO public.complaint_categories VALUES (8, 'Water Supply Issue', 'Broken pipes or lack of water supply in the area', true, NULL, NULL, 4);


--
-- Data for Name: contact_diaries; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.contact_diaries VALUES (1, 'asdvjhv', 'gjsahvdjashv', 'hsgvjahvv', '9876543210', 'auqfug@gmail.com', true, 2, '2026-03-12 17:02:31.946831+00');


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.departments VALUES (1, 'Urban Local Body (ULB)', 'ULB', 'Municipal', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (2, 'Urban Improvement Trust (UIT)', 'UIT', 'Municipal', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (3, 'Town Planning Department', 'TP', 'Planning', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (4, 'Engineering (Civil) Department', 'ENG', 'Engineering', false, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (5, 'Legal & Enforcement Department', 'LEG', 'Regulatory', false, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (6, 'Land & Records Department', 'LND', 'Records', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (7, 'Environment & Public Health Dept.', 'EPH', 'Monitoring', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.departments VALUES (8, 'ufsu', 'hgvsjahf', 'Planning', true, '2026-02-27 08:44:31.277567', 2);


--
-- Data for Name: downloads; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.downloads VALUES (1, 'Building Bylaws 2024', 'Guidelines', 1, 'Guidelines for building construction', 'dummy/path.pdf', 'ACTIVE', 2, '2026-02-22 10:09:55.006381+00');
INSERT INTO public.downloads VALUES (2, 'sajhhgvshdvf', 'Guidelines', 2, NULL, 'documents/downloads/659debc4-7017-453c-82f9-8171a4ff0194/cshell_install.sh', 'ACTIVE', 2, '2026-02-25 10:40:39.48783+00');
INSERT INTO public.downloads VALUES (3, 'asidgasidg', 'Guidelines', 1, NULL, 'documents/downloads/5c3a7215-3b7e-4402-8445-42f55176d8a9/06aff053-4acc-4a66-8fb1-78f29c3b73d1.pdf', 'ACTIVE', 2, '2026-02-27 08:39:14.407014+00');
INSERT INTO public.downloads VALUES (4, 'asidgasidg', 'Guidelines', 1, NULL, 'documents/downloads/66f280ed-b52c-462f-abee-1c363a0e3cd9/Dual_wallpaper.jpeg', 'ACTIVE', 2, '2026-02-27 08:39:44.049315+00');
INSERT INTO public.downloads VALUES (5, 'ajhfvkihv', 'Application Form', 4, NULL, 'documents/downloads/51725e73-9ee0-4151-a740-e56d875d2565/gwen.jpeg', 'ACTIVE', 2, '2026-02-27 16:32:31.746603+00');


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.events VALUES (1, 'Summer Festival 2025', 'Cultural', '2026-04-22 10:09:55.006381+00', 'Nakki Lake', 'ACTIVE', 2, '2026-02-22 10:09:55.006381+00');
INSERT INTO public.events VALUES (2, 'snasdnl', 'Public Program', '2026-03-11 19:09:51.719+00', 'sdjlasjbd', 'ACTIVE', 2, '2026-03-11 19:10:21.526377+00');


--
-- Data for Name: leaders; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.leaders VALUES (1, 'Shri Mahant Ji', 'Chairman', '2025-02-22 10:09:55.006381+00', NULL, 'ACTIVE', 2, '2026-02-22 10:09:55.006381+00');
INSERT INTO public.leaders VALUES (2, 'sagig', 'jagiksg', '2026-02-27 08:44:42.959+00', '2026-02-12 00:00:00+00', 'ACTIVE', 2, '2026-02-27 08:45:21.53474+00');
INSERT INTO public.leaders VALUES (3, 'vikas', 'sdm', '2026-02-27 16:29:24.789+00', '2026-03-27 00:00:00+00', 'ACTIVE', 2, '2026-02-27 16:30:03.981744+00');
INSERT INTO public.leaders VALUES (4, 'vijay', 'siahbih', '2026-02-27 16:30:08.578+00', '2026-07-27 00:00:00+00', 'ACTIVE', 2, '2026-02-27 16:30:51.361657+00');


--
-- Data for Name: materials; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.materials VALUES (1, 'Cement (OPC)', 'Bags', NULL, NULL);
INSERT INTO public.materials VALUES (2, 'Reinforcement Steel', 'Tons', NULL, NULL);
INSERT INTO public.materials VALUES (3, 'Red Bricks', 'Units', NULL, NULL);
INSERT INTO public.materials VALUES (4, 'River Sand', 'Cubic Meters', NULL, NULL);
INSERT INTO public.materials VALUES (5, 'Wall Tiles', 'Units', NULL, NULL);
INSERT INTO public.materials VALUES (6, 'PVC Pipes', 'Units', NULL, NULL);


--
-- Data for Name: notices; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.notices VALUES (1, 'Guidelines for New Construction Applications', 'Public Notice', '2026-02-22 10:09:55.006381+00', '2026-03-22 10:09:55.006381+00', 'ACTIVE', 'PUBLIC', 2, '2026-02-22 10:09:55.006381+00');
INSERT INTO public.notices VALUES (2, 'asdjnls', 'Public Notice', '2026-03-11 19:09:16.73+00', '2026-03-28 00:00:00+00', 'ACTIVE', 'PUBLIC', 2, '2026-03-11 19:09:32.549711+00');
INSERT INTO public.notices VALUES (3, 'ahfhiuh', 'Public Notice', '2026-03-11 19:15:49.693+00', '2026-03-21 00:00:00+00', 'ACTIVE', 'PUBLIC', 2, '2026-03-11 19:16:23.359097+00');
INSERT INTO public.notices VALUES (4, 'a', 'Public Notice', '2026-03-11 19:15:49.693+00', '2026-03-21 00:00:00+00', 'ACTIVE', 'PUBLIC', 2, '2026-03-11 19:17:27.765707+00');
INSERT INTO public.notices VALUES (5, 'hey', 'Public Notice', '2026-03-11 19:19:16.525+00', '2026-03-19 00:00:00+00', 'ACTIVE', 'PUBLIC', 2, '2026-03-11 19:21:42.211881+00');
INSERT INTO public.notices VALUES (6, 'new', 'Public Notice', '2026-03-12 16:54:50.139+00', '2026-03-25 00:00:00+00', 'ACTIVE', 'PUBLIC', 2, '2026-03-12 16:55:54.722831+00');


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.roles VALUES (1, 'Super Admin', 'SA', 'Full access', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.roles VALUES (2, 'Nodal Officer', 'NO', 'All files', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.roles VALUES (3, 'Commissioner', 'COM', 'Department files', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.roles VALUES (4, 'Junior Engineer (JEN)', 'JEN', 'Site inspection', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.roles VALUES (5, 'ATP / Land / Legal', 'ATP', 'Scrutiny', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.roles VALUES (6, 'Naka Incharge', 'NKI', 'Vehicle entry', true, '2026-02-20 14:24:54.721206', 2);


--
-- Data for Name: tenders; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.tenders VALUES (1, 'Construction of Public Toilets at Nakki Lake', 'Civil Works', 1, 50000000.00, '2026-02-22 10:09:55.006381+00', '2026-03-14 10:09:55.006381+00', 'ACTIVE', 2, '2026-02-22 10:09:55.006381+00');
INSERT INTO public.tenders VALUES (2, 'hohojh', 'Standard', 3, 5100000.00, '2026-03-11 19:19:16.525+00', '2026-03-28 00:00:00+00', 'ACTIVE', 2, '2026-03-11 19:22:06.352264+00');


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.users VALUES (1, 'CITIZEN', 'garvit', '7415275801', NULL, NULL);
INSERT INTO public.users VALUES (2, 'SUPERADMIN', 'Super Admin', '9827084709', 'test@123', '$2b$12$okrQgJKsHV2scOhQq273JuINtjAUXhHVTxkM2bcZ9L6bpu0GqTmwS');
INSERT INTO public.users VALUES (3, 'NODAL_OFFICER', 'Nodal Officer', '9876543210', 'nodal_officer', '$2b$12$GVQP8Yh378FWEdWMPieB8eIWvj5x25HCYN7RDttIZ9wNJ3QXpqbQS');
INSERT INTO public.users VALUES (4, 'COMMISSIONER', 'Commissioner', '9876543211', 'commissioner', '$2b$12$A3/5h8y09mfEoxihVbYvK.VAL9PWTYEYOoTO6O3wfN2vXNtIKwMgu');
INSERT INTO public.users VALUES (5, 'DEPT_LAND', 'Land Department', '9876543213', 'dept_land', '$2b$12$ZDO.0KbLv/.sno3g1kd.weAu18wGQfUPILvFvCIJglrlwBLGKKC7.');
INSERT INTO public.users VALUES (6, 'DEPT_LEGAL', 'Legal Department', '9876543214', 'dept_legal', '$2b$12$o5zWKoHnMLrrniyoh/v9Futa0MeVSrsrlM7G7mXd.QeDp30bA1gEm');
INSERT INTO public.users VALUES (7, 'DEPT_ATP', 'ATP Department', '9876543215', 'dept_atp', '$2b$12$9yhw7ZG1AdSIaDTTwzvO6O1PcllNtJvngdlri67f2s/Tj.bqAs1Ku');
INSERT INTO public.users VALUES (8, 'NAKA_INCHARGE', 'Naka Incharge', '9876543216', 'naka_incharge', '$2b$12$IUYEKqNrV1r/17MyADxNqO8OPlKom4PRWZ8xDaMqtlyIoQw1c7FC.');
INSERT INTO public.users VALUES (9, 'JEN', 'Junior Engineer', '9876543212', 'jen', '$2b$12$3Ihe.RBgwDLB/qhcLm49MeQcPCeuZ28dZSJ4Ku0rKFUqm5sWzGqTG');


--
-- Data for Name: wards; Type: TABLE DATA; Schema: public; Owner: etoken_user
--

INSERT INTO public.wards VALUES (1, 'Nakki Lake', 'W01', 'Ward', 'Area surrounding Nakki Lake', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (2, 'Delwara Road', 'W02', 'Ward', 'Area along Delwara Road', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (3, 'Abu Road Link', 'W03', 'Ward', 'Area connecting to Abu Road', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (4, 'Sunset Point Zone', 'Z01', 'Zone', 'Sunset Point tourism zone', false, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (5, 'Achalgarh Zone', 'Z02', 'Zone', 'Achalgarh historical zone', false, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (6, 'Gaumukh', 'W04', 'Ward', 'Gaumukh temple area', true, '2026-02-20 14:24:54.721206', 2);
INSERT INTO public.wards VALUES (7, 'Peace Park Zone', 'Z03', 'Zone', 'Peace Park ecological zone', true, '2026-02-20 14:24:54.721206', 2);


--
-- Name: active_user_otps_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.active_user_otps_id_seq', 22, true);


--
-- Name: application_action_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_action_logs_id_seq', 11, true);


--
-- Name: application_approvals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_approvals_id_seq', 11, true);


--
-- Name: application_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_comments_id_seq', 6, true);


--
-- Name: application_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_documents_id_seq', 52, true);


--
-- Name: application_materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_materials_id_seq', 54, true);


--
-- Name: application_phase_materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_phase_materials_id_seq', 12, true);


--
-- Name: application_phases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.application_phases_id_seq', 2, true);


--
-- Name: applications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.applications_id_seq', 7, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 132, true);


--
-- Name: city_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.city_profiles_id_seq', 7, true);


--
-- Name: complaint_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.complaint_categories_id_seq', 9, true);


--
-- Name: complaint_comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.complaint_comments_id_seq', 1, false);


--
-- Name: complaint_media_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.complaint_media_id_seq', 1, true);


--
-- Name: complaints_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.complaints_id_seq', 1, true);


--
-- Name: contact_diaries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.contact_diaries_id_seq', 1, true);


--
-- Name: departments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.departments_id_seq', 8, true);


--
-- Name: downloads_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.downloads_id_seq', 5, true);


--
-- Name: events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.events_id_seq', 2, true);


--
-- Name: inspection_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.inspection_reports_id_seq', 3, true);


--
-- Name: leaders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.leaders_id_seq', 4, true);


--
-- Name: materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.materials_id_seq', 6, true);


--
-- Name: notices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.notices_id_seq', 6, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.roles_id_seq', 6, true);


--
-- Name: tenders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.tenders_id_seq', 2, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.users_id_seq', 9, true);


--
-- Name: vehicle_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.vehicle_entries_id_seq', 1, false);


--
-- Name: vehicle_materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.vehicle_materials_id_seq', 1, false);


--
-- Name: wards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: etoken_user
--

SELECT pg_catalog.setval('public.wards_id_seq', 7, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: city_profiles city_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.city_profiles
    ADD CONSTRAINT city_profiles_pkey PRIMARY KEY (id);


--
-- Name: complaint_categories complaint_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT complaint_categories_pkey PRIMARY KEY (id);


--
-- Name: contact_diaries contact_diaries_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.contact_diaries
    ADD CONSTRAINT contact_diaries_pkey PRIMARY KEY (id);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: downloads downloads_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.downloads
    ADD CONSTRAINT downloads_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: leaders leaders_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.leaders
    ADD CONSTRAINT leaders_pkey PRIMARY KEY (id);


--
-- Name: materials materials_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_pkey PRIMARY KEY (id);


--
-- Name: notices notices_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.notices
    ADD CONSTRAINT notices_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: tenders tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: wards wards_pkey; Type: CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT wards_pkey PRIMARY KEY (id);


--
-- Name: ix_city_profiles_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_city_profiles_id ON public.city_profiles USING btree (id);


--
-- Name: ix_complaint_categories_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_complaint_categories_id ON public.complaint_categories USING btree (id);


--
-- Name: ix_complaint_categories_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_complaint_categories_name ON public.complaint_categories USING btree (name);


--
-- Name: ix_contact_diaries_contact_person; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_contact_diaries_contact_person ON public.contact_diaries USING btree (contact_person);


--
-- Name: ix_contact_diaries_designation; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_contact_diaries_designation ON public.contact_diaries USING btree (designation);


--
-- Name: ix_contact_diaries_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_contact_diaries_id ON public.contact_diaries USING btree (id);


--
-- Name: ix_contact_diaries_office_department; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_contact_diaries_office_department ON public.contact_diaries USING btree (office_department);


--
-- Name: ix_contact_diaries_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_contact_diaries_status ON public.contact_diaries USING btree (status);


--
-- Name: ix_departments_code; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE UNIQUE INDEX ix_departments_code ON public.departments USING btree (code);


--
-- Name: ix_departments_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_departments_id ON public.departments USING btree (id);


--
-- Name: ix_departments_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_departments_name ON public.departments USING btree (name);


--
-- Name: ix_downloads_department_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_downloads_department_id ON public.downloads USING btree (department_id);


--
-- Name: ix_downloads_document_title; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_downloads_document_title ON public.downloads USING btree (document_title);


--
-- Name: ix_downloads_document_type; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_downloads_document_type ON public.downloads USING btree (document_type);


--
-- Name: ix_downloads_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_downloads_id ON public.downloads USING btree (id);


--
-- Name: ix_downloads_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_downloads_status ON public.downloads USING btree (status);


--
-- Name: ix_events_event_type; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_events_event_type ON public.events USING btree (event_type);


--
-- Name: ix_events_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_events_id ON public.events USING btree (id);


--
-- Name: ix_events_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_events_status ON public.events USING btree (status);


--
-- Name: ix_events_title; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_events_title ON public.events USING btree (title);


--
-- Name: ix_leaders_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_leaders_id ON public.leaders USING btree (id);


--
-- Name: ix_leaders_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_leaders_name ON public.leaders USING btree (name);


--
-- Name: ix_leaders_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_leaders_status ON public.leaders USING btree (status);


--
-- Name: ix_materials_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_materials_id ON public.materials USING btree (id);


--
-- Name: ix_materials_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_materials_name ON public.materials USING btree (name);


--
-- Name: ix_materials_unit; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_materials_unit ON public.materials USING btree (unit);


--
-- Name: ix_notices_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_notices_id ON public.notices USING btree (id);


--
-- Name: ix_notices_notice_type; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_notices_notice_type ON public.notices USING btree (notice_type);


--
-- Name: ix_notices_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_notices_status ON public.notices USING btree (status);


--
-- Name: ix_notices_title; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_notices_title ON public.notices USING btree (title);


--
-- Name: ix_notices_visibility; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_notices_visibility ON public.notices USING btree (visibility);


--
-- Name: ix_roles_code; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE UNIQUE INDEX ix_roles_code ON public.roles USING btree (code);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_tenders_department_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_tenders_department_id ON public.tenders USING btree (department_id);


--
-- Name: ix_tenders_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_tenders_id ON public.tenders USING btree (id);


--
-- Name: ix_tenders_status; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_tenders_status ON public.tenders USING btree (status);


--
-- Name: ix_tenders_tender_type; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_tenders_tender_type ON public.tenders USING btree (tender_type);


--
-- Name: ix_tenders_title; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_tenders_title ON public.tenders USING btree (title);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_mobile; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_mobile ON public.users USING btree (mobile);


--
-- Name: ix_users_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_name ON public.users USING btree (name);


--
-- Name: ix_users_password; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_password ON public.users USING btree (password);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_wards_code; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE UNIQUE INDEX ix_wards_code ON public.wards USING btree (code);


--
-- Name: ix_wards_id; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_wards_id ON public.wards USING btree (id);


--
-- Name: ix_wards_name; Type: INDEX; Schema: public; Owner: etoken_user
--

CREATE INDEX ix_wards_name ON public.wards USING btree (name);


--
-- Name: city_profiles city_profiles_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.city_profiles
    ADD CONSTRAINT city_profiles_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: complaint_categories complaint_categories_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT complaint_categories_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: complaint_categories complaint_categories_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT complaint_categories_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: contact_diaries contact_diaries_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.contact_diaries
    ADD CONSTRAINT contact_diaries_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: departments departments_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: downloads downloads_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.downloads
    ADD CONSTRAINT downloads_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: downloads downloads_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.downloads
    ADD CONSTRAINT downloads_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: events events_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: leaders leaders_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.leaders
    ADD CONSTRAINT leaders_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: materials materials_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: notices notices_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.notices
    ADD CONSTRAINT notices_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: roles roles_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: tenders tenders_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: tenders tenders_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: wards wards_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: etoken_user
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT wards_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict m7wxAxJGF6SYDYgdOwWtPHbWIwA38wsB7wiQp450VnkQ7sQlzMWhgnKHZQWkbUO

