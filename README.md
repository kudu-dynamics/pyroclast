<!--
*** Thanks for checking out this README Template. If you have a suggestion that would
*** make this better, please fork the repo and create a pull request or simply open
*** an issue with the tag "enhancement".
*** Thanks again! Now go create something AMAZING! :D
***
***
***
*** To avoid retyping too much info. Do a search and replace for the following:
*** github_username, repo, twitter_handle, email
-->


<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
<!--
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]
-->


<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="/">
    <img src="static/images/volcano.png" alt="Pyroclast Logo" width="80" height="80">
  </a>

  <h3 align="center">Pyroclast</h3>

  <p align="center">
    A Python Cloud Development Kit -- similar to [Go CDK](https://gocloud.dev)
  </p>

  <p>
    Icon made by [Freepik](https://www.flaticon.com/authors/freepik) from [www.flaticon.com](https://www.flaticon.com)
  </p>
</p>


<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
  * [Built With](#built-with)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)


<!-- ABOUT THE PROJECT -->
## About The Project

Pyroclast is a library meant to simplify interactions with common backend APIs.

The efforts within aim to hopefully reduce the chance of expensive vendor
lock-in choices and provide expert knowledge on how to integrate with certain
tools (e.g. NATS provides an unopinionated asyncio client that needs a lot of
understanding to use properly).

### Built With

* [asyncio-nats-client](https://pypi.org/project/asyncio-nats-client/)
* [asyncio-nats-streaming](https://pypi.org/project/asyncio-nats-streaming/)
* [namesgenerator](https://pypi.org/project/namesgenerator/)
* [pydgraph](https://pypi.org/project/pydgraph/)
* [python-nomad](https://pypi.org/project/python-nomad/)
* [redis](https://pypi.org/project/redis/)
* [s3](https://pypi.org/project/boto3/)
* [sonic](https://pypi.org/project/asonic/)
* [tenacity](https://pypi.org/project/tenacity/)


<!-- GETTING STARTED -->
## Getting Started

To get the library installed locally.

### Prerequisites

Install the prerequisite libraries/utilities.

* plexiglass

If you have a private pypi repository setup,

```sh
pip install --trusted-host 10.1.7.4 -i http://10.1.7.4:8050 plexiglass
```

If you have the source code available.

```sh
git clone https://github.com/kudu/plexiglass
pip install plexiglass
```

* poetry (optional)

```sh
pip install poetry
poetry config virtualenvs.create false
poetry install
```

### Installation

1. Clone the repo.

```sh
git clone https://github.com/kudu/pyroclast
```

* pip

2. Install the package with any extra backends.

```sh
pip install .[redis, s3]
```

* poetry

2. Clone the repo and install with whatever backends are needed.

```sh
poetry install -E redis -E s3
```


<!-- USAGE EXAMPLES -->
## Usage

Check the examples

- [nats_consumer](examples/nats_consumer.py)
- [redis_basic](examples/redis_basic.py)
- [stan_basic](examples/stan_basic.py)


<!-- DEVELOPING -->
## Developing

### Updating Dependencies

Poetry is the tool for updating dependencies.
Dephell is used to convert the `pyproject.toml` file to `setup.py`.

```sh
# The lock file will contain any newly updated dependency versions.
# Which we then automatically populate the `setup.py` file with.
poetry update

dephell convert deps

# DEV: Until https://github.com/dephell/dephell/issues/178 is resolved
#      Remove the `README.rst` and point to `README.md` manually instead.

rm -f README.rst
sed -i 's#README.rst#README.md#' setup.py
```


<!-- ROADMAP -->
## Roadmap

See the project's issue tracker for a list of proposed features (and known issues).


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


<!-- LICENSE -->
## License

XXX: Proprietary? Can we MIT this?


<!-- CONTACT -->
## Contact

Eric Lee - @elee - elee@kududyn.com

Distribution Statement "A" (Approved for Public Release, Distribution
Unlimited).
