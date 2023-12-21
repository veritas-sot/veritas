SQL database and tables

*database*

CREATE DATABASE journal OWNER postgres;

*enum*

CREATE TYPE status AS ENUM ('active', 'closed', 'error');

*tables*

CREATE TABLE IF NOT EXISTS public.metadata
(
    uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    started timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    status status DEFAULT 'active'::status,
    CONSTRAINT metadata_pkey PRIMARY KEY (uuid)
);

CREATE TABLE IF NOT EXISTS public.entries
(
    id serial NOT NULL,
    uuid uuid NOT NULL,
    app character varying(20) COLLATE pg_catalog."default",
    message text COLLATE pg_catalog."default",
    CONSTRAINT entries_pkey PRIMARY KEY (uuid),
    CONSTRAINT uuid FOREIGN KEY (uuid)
        REFERENCES public.metadata (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS public.log
(
    id integer NOT NULL DEFAULT nextval('log_id_seq'::regclass),
    date timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    name character varying(1024) COLLATE pg_catalog."default",
    levelno integer,
    levelname character varying(10) COLLATE pg_catalog."default",
    module character varying(100) COLLATE pg_catalog."default",
    processname character varying(100) COLLATE pg_catalog."default",
    func character varying(100) COLLATE pg_catalog."default",
    lineno integer,
    message character varying(1024) COLLATE pg_catalog."default",
    pathname character varying(1024) COLLATE pg_catalog."default",
    CONSTRAINT log_pkey PRIMARY KEY (id)
)
