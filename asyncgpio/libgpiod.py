# -*- coding: utf-8 -*-

# Copyright (c) 2018 Matthias Urlichs <matthias@urlichs.de>
# Based on work Copyright (c) 2018 Steven P. Goldsmith
"""
libgpiod CFFI interface
-------------

This is a stripped-down version which doesn't do "bulk" access (no point IMHO)
and doesn't implement an event loop (that's Trio's job).
"""

from cffi import FFI

__all__ = [
    "DIRECTION_INPUT",
    "DIRECTION_OUTPUT",
    "ACTIVE_STATE_HIGH",
    "ACTIVE_STATE_LOW",
    "REQUEST_DIRECTION_AS_IS",
    "REQUEST_DIRECTION_INPUT",
    "REQUEST_DIRECTION_OUTPUT",
    "REQUEST_EVENT_FALLING_EDGE",
    "REQUEST_EVENT_RISING_EDGE",
    "REQUEST_EVENT_BOTH_EDGES",
    "REQUEST_FLAG_OPEN_DRAIN",
    "REQUEST_FLAG_OPEN_SOURCE",
    "REQUEST_FLAG_ACTIVE_LOW",
    "EVENT_RISING_EDGE",
    "EVENT_FALLING_EDGE",
    "ffi",
    "lib",
]

ffi = FFI()
ffi.cdef(
    """
enum {
    GPIOD_CTXLESS_EVENT_CB_TIMEOUT = 1,
    GPIOD_CTXLESS_EVENT_CB_RISING_EDGE,
    GPIOD_CTXLESS_EVENT_CB_FALLING_EDGE,
};

enum {
    GPIOD_CTXLESS_EVENT_CB_RET_ERR = -1,
    GPIOD_CTXLESS_EVENT_CB_RET_OK = 0,
    GPIOD_CTXLESS_EVENT_CB_RET_STOP = 1,
};

enum {
    GPIOD_CTXLESS_EVENT_POLL_RET_STOP = -2,
    GPIOD_CTXLESS_EVENT_POLL_RET_ERR = -1,
    GPIOD_CTXLESS_EVENT_POLL_RET_TIMEOUT = 0,
};

enum {
    GPIOD_LINE_DIRECTION_INPUT = 1,
    GPIOD_LINE_DIRECTION_OUTPUT,
};

enum {
    GPIOD_LINE_ACTIVE_STATE_HIGH = 1,
    GPIOD_LINE_ACTIVE_STATE_LOW,
};

enum {
    GPIOD_LINE_REQUEST_DIRECTION_AS_IS = 1,
    GPIOD_LINE_REQUEST_DIRECTION_INPUT,
    GPIOD_LINE_REQUEST_DIRECTION_OUTPUT,
    GPIOD_LINE_REQUEST_EVENT_FALLING_EDGE,
    GPIOD_LINE_REQUEST_EVENT_RISING_EDGE,
    GPIOD_LINE_REQUEST_EVENT_BOTH_EDGES,
};

enum {
    GPIOD_LINE_REQUEST_FLAG_OPEN_DRAIN = 1,
    GPIOD_LINE_REQUEST_FLAG_OPEN_SOURCE = 2,
    GPIOD_LINE_REQUEST_FLAG_ACTIVE_LOW = 4,
    GPIOD_LINE_REQUEST_FLAG_BIAS_DISABLE = 8,
    GPIOD_LINE_REQUEST_FLAG_BIAS_PULL_DOWN = 16,
    GPIOD_LINE_REQUEST_FLAG_BIAS_PULL_UP = 32,
};

enum {
    GPIOD_LINE_EVENT_RISING_EDGE = 1,
    GPIOD_LINE_EVENT_FALLING_EDGE,
};

struct timespec {
    long tv_sec;
    long tv_nsec;
};

struct gpiod_line {
    unsigned int offset;
    int direction;
    int active_state;
    bool used;
    bool open_source;
    bool open_drain;
    int state;
    bool up_to_date;
    struct gpiod_chip *chip;
    int fd;
    char name[32];
    char consumer[32];
};

struct gpiod_chip {
    struct gpiod_line **lines;
    unsigned int num_lines;
    int fd;
    char name[32];
    char label[32];
};

struct gpiod_ctxless_event_poll_fd {
    int fd;
    /**< File descriptor number. */
    bool event;
    /**< Indicates whether an event occurred on this file descriptor. */
};

struct gpiod_line_request_config {
    const char *consumer;
    int request_type;
    int flags;
};

struct gpiod_line_event {
    struct timespec ts;
    int event_type;
};

struct gpiod_chip;

struct gpiod_line;

struct gpiod_chip_iter;

struct gpiod_line_iter;

struct gpiod_line_bulk;

typedef void (*gpiod_ctxless_set_value_cb)(void *);

typedef int (*gpiod_ctxless_event_handle_cb)(int, unsigned int,
                            const struct timespec *, void *);

typedef int (*gpiod_ctxless_event_poll_cb)(unsigned int,
                struct gpiod_ctxless_event_poll_fd *,
                const struct timespec *, void *);

int gpiod_ctxless_set_value(const char *device, unsigned int offset, int value,
                bool active_low, const char *consumer,
                gpiod_ctxless_set_value_cb cb,
                void *data);

int gpiod_ctxless_set_value_multiple(const char *device,
                        const unsigned int *offsets,
                        const int *values, unsigned int num_lines,
                        bool active_low, const char *consumer,
                        gpiod_ctxless_set_value_cb cb,
                        void *data);

int gpiod_ctxless_find_line(const char *name, char *chipname,
                size_t chipname_size,
                unsigned int *offset);

int gpiod_chip_find_lines(struct gpiod_chip *chip, const char **names,
                         struct gpiod_line_bulk *bulk);

struct gpiod_chip *gpiod_chip_open(const char *path);

struct gpiod_chip *gpiod_chip_open_by_name(const char *name);

struct gpiod_chip *gpiod_chip_open_by_number(unsigned int num);

struct gpiod_chip *gpiod_chip_open_by_label(const char *label);

struct gpiod_chip *gpiod_chip_open_lookup(const char *descr);

void gpiod_chip_close(struct gpiod_chip *chip);

const char *gpiod_chip_name(struct gpiod_chip *chip);

const char *gpiod_chip_label(struct gpiod_chip *chip);

unsigned int gpiod_chip_num_lines(struct gpiod_chip *chip);

struct gpiod_line *
gpiod_chip_get_line(struct gpiod_chip *chip, unsigned int offset);

int gpiod_chip_get_lines(struct gpiod_chip *chip,
                         unsigned int *offsets, unsigned int num_offsets,
                         struct gpiod_line_bulk *bulk);

int gpiod_chip_get_all_lines(struct gpiod_chip *chip,
                             struct gpiod_line_bulk *bulk);

struct gpiod_line *
gpiod_chip_find_line(struct gpiod_chip *chip, const char *name);

unsigned int gpiod_line_offset(struct gpiod_line *line);

const char *gpiod_line_name(struct gpiod_line *line);

const char *gpiod_line_consumer(struct gpiod_line *line);

int gpiod_line_direction(struct gpiod_line *line);

int gpiod_line_active_state(struct gpiod_line *line);

bool gpiod_line_is_used(struct gpiod_line *line);

bool gpiod_line_is_open_drain(struct gpiod_line *line);

bool gpiod_line_is_open_source(struct gpiod_line *line);

int gpiod_line_update(struct gpiod_line *line);

bool gpiod_line_needs_update(struct gpiod_line *line);

int gpiod_line_request(struct gpiod_line *line,
                const struct gpiod_line_request_config *config,
                int default_val);

int gpiod_line_request_input(struct gpiod_line *line,
                    const char *consumer);

int gpiod_line_request_output(struct gpiod_line *line,
                    const char *consumer, int default_val);

int gpiod_line_request_rising_edge_events(struct gpiod_line *line,
                        const char *consumer);

int gpiod_line_request_falling_edge_events(struct gpiod_line *line,
                        const char *consumer);

int gpiod_line_request_both_edges_events(struct gpiod_line *line,
                        const char *consumer);

int gpiod_line_request_input_flags(struct gpiod_line *line,
                    const char *consumer, int flags);

int gpiod_line_request_output_flags(struct gpiod_line *line,
                    const char *consumer, int flags,
                    int default_val);

int gpiod_line_request_rising_edge_events_flags(struct gpiod_line *line,
                        const char *consumer,
                        int flags);

int gpiod_line_request_falling_edge_events_flags(struct gpiod_line *line,
                            const char *consumer,
                            int flags);

int gpiod_line_request_both_edges_events_flags(struct gpiod_line *line,
                            const char *consumer,
                            int flags);

void gpiod_line_release(struct gpiod_line *line);

bool gpiod_line_is_requested(struct gpiod_line *line);

bool gpiod_line_is_free(struct gpiod_line *line);

int gpiod_line_get_value(struct gpiod_line *line);

int gpiod_line_set_value(struct gpiod_line *line, int value);

int gpiod_line_set_value_bulk(struct gpiod_line_bulk *bulk,
                              const int *values);

int gpiod_line_event_wait(struct gpiod_line *line,
                const struct timespec *timeout);

int gpiod_line_event_read(struct gpiod_line *line,
                struct gpiod_line_event *event);

int gpiod_line_event_get_fd(struct gpiod_line *line);

int gpiod_line_event_read_fd(int fd, struct gpiod_line_event *event);

struct gpiod_line *
gpiod_line_get(const char *device, unsigned int offset);

struct gpiod_line *gpiod_line_find(const char *name);

void gpiod_line_close_chip(struct gpiod_line *line);

struct gpiod_chip *gpiod_line_get_chip(struct gpiod_line *line);

struct gpiod_chip_iter *gpiod_chip_iter_new(void);

void gpiod_chip_iter_free(struct gpiod_chip_iter *iter);

void gpiod_chip_iter_free_noclose(struct gpiod_chip_iter *iter);

struct gpiod_chip *
gpiod_chip_iter_next(struct gpiod_chip_iter *iter);

struct gpiod_chip *
gpiod_chip_iter_next_noclose(struct gpiod_chip_iter *iter);

struct gpiod_line_iter *
gpiod_line_iter_new(struct gpiod_chip *chip);

void gpiod_line_iter_free(struct gpiod_line_iter *iter);

struct gpiod_line *
gpiod_line_iter_next(struct gpiod_line_iter *iter);

const char *gpiod_version_string(void);
"""
)

try:
    lib = ffi.dlopen("libgpiod.so.2")
except OSError:
    lib = ffi.dlopen("c")  # workaround if we're only building docs

DIRECTION_INPUT = lib.GPIOD_LINE_REQUEST_DIRECTION_INPUT
DIRECTION_OUTPUT = lib.GPIOD_LINE_REQUEST_DIRECTION_OUTPUT
ACTIVE_STATE_HIGH = lib.GPIOD_LINE_ACTIVE_STATE_HIGH
ACTIVE_STATE_LOW = lib.GPIOD_LINE_ACTIVE_STATE_LOW
REQUEST_DIRECTION_AS_IS = lib.GPIOD_LINE_REQUEST_DIRECTION_AS_IS
REQUEST_DIRECTION_INPUT = lib.GPIOD_LINE_REQUEST_DIRECTION_INPUT
REQUEST_DIRECTION_OUTPUT = lib.GPIOD_LINE_REQUEST_DIRECTION_OUTPUT
REQUEST_EVENT_FALLING_EDGE = lib.GPIOD_LINE_REQUEST_EVENT_FALLING_EDGE
REQUEST_EVENT_RISING_EDGE = lib.GPIOD_LINE_REQUEST_EVENT_RISING_EDGE
REQUEST_EVENT_BOTH_EDGES = lib.GPIOD_LINE_REQUEST_EVENT_BOTH_EDGES

REQUEST_FLAG_OPEN_DRAIN = lib.GPIOD_LINE_REQUEST_FLAG_OPEN_DRAIN
REQUEST_FLAG_OPEN_SOURCE = lib.GPIOD_LINE_REQUEST_FLAG_OPEN_SOURCE
REQUEST_FLAG_ACTIVE_LOW = lib.GPIOD_LINE_REQUEST_FLAG_ACTIVE_LOW
EVENT_RISING_EDGE = lib.GPIOD_LINE_EVENT_RISING_EDGE
EVENT_FALLING_EDGE = lib.GPIOD_LINE_EVENT_FALLING_EDGE
