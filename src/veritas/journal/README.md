SQL database and tables

*database*

CREATE DATABASE journal OWNER postgres;

*enum*

CREATE TYPE status AS ENUM ('active', 'closed', 'error');

*tables*

**journals**

CREATE TABLE public.journals
(
    uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    opened timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed timestamp with time zone,
    status status DEFAULT 'active'::status,
    PRIMARY KEY (uuid)
);

COMMENT ON TABLE public.journals
    IS 'list of active and completed journals';

**activities**

CREATE TABLE public.activities
(
    id serial,
    uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    journal_uuid uuid NOT NULL,
    app character varying(100),
    activity character varying(200) NOT NULL,
    started timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT unique_uuid UNIQUE (uuid),
    CONSTRAINT jrnl_uuid FOREIGN KEY (journal_uuid)
        REFERENCES public.journals (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
        NOT VALID
);

**logs**

CREATE TABLE IF NOT EXISTS public.logs
(
    id serial NOT NULL,
    uuid uuid,
    app character varying(100) COLLATE pg_catalog."default",
    date timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    levelno integer,
    levelname character varying(10) COLLATE pg_catalog."default",
    function character varying(1024) COLLATE pg_catalog."default",
    functionname character varying(1024) COLLATE pg_catalog."default",
    module character varying(100) COLLATE pg_catalog."default",
    processname character varying(100) COLLATE pg_catalog."default",
    threadname character varying(100) COLLATE pg_catalog."default",
    lineno integer,
    message character varying(1024) COLLATE pg_catalog."default",
    filename character varying(1024) COLLATE pg_catalog."default",
    pathname character varying(1024) COLLATE pg_catalog."default",
    exception character varying(1024) COLLATE pg_catalog."default",
    extra character varying(1024) COLLATE pg_catalog."default",
    CONSTRAINT log_pkey PRIMARY KEY (id),
    CONSTRAINT activity_uuid FOREIGN KEY (uuid)
        REFERENCES public.activities (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
        NOT VALID
);

**results**

CREATE TABLE IF NOT EXISTS public.results
(
    id serial NOT NULL,
    uuid uuid,
    app character varying(100) COLLATE pg_catalog."default",
    entity character varying(80) COLLATE pg_catalog."default",
    message character varying(1024) COLLATE pg_catalog."default",
    CONSTRAINT results_pkey PRIMARY KEY (id),
    CONSTRAINT activity_uuid FOREIGN KEY (uuid)
        REFERENCES public.activities (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
        NOT VALID
)

**messages**

CREATE TABLE public.messages
(
    id serial,
    uuid uuid,
    app character varying(80),
    message text,
    PRIMARY KEY (id),
    CONSTRAINT msg_uuid FOREIGN KEY (uuid)
        REFERENCES public.journals (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL
        NOT VALID
);

**store**

CREATE TABLE public.store
(
    app character varying(80) NULL,
    key character varying(1024) NOT NULL,
    value character varying(1024) NOT NULL,
    CONSTRAINT primary_key PRIMARY KEY (key, value, app)
);
