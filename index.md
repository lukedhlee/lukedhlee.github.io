---
layout: default
title: Home
---

<section class="hero">
  <div class="profile-art" aria-hidden="true">
    <img src="{{ '/assets/img/profile-mark.svg' | relative_url }}" alt="">
  </div>
  <div class="hero-copy">
    <p class="eyebrow">Ph.D. student · UC Berkeley</p>
    <h1>Luke Lee</h1>
    <p class="lead">
      I am a Ph.D. student at UC Berkeley studying large language models.
      My research interests include LLM reasoning, agents, evaluation, and systems for reliable AI.
    </p>
    <div class="link-row">
      <a href="https://github.com/lukedhlee">GitHub</a>
      <a href="{{ '/publications/' | relative_url }}">Publications</a>
      <a href="{{ '/blog/' | relative_url }}">Blog</a>
      <a href="#" aria-disabled="true">CV</a>
    </div>
  </div>
</section>

<section class="section">
  <h2>About</h2>
  <p>
    I work on questions around how large language models reason, use tools, interact with environments,
    and can be evaluated in ways that reflect real-world use. I am broadly interested in building AI systems
    that are capable, understandable, and dependable.
  </p>
  <p>
    Before and during graduate school, I have been interested in research at the intersection of machine learning,
    language, infrastructure, and human-facing applications.
  </p>
</section>

<section class="section">
  <div class="section-heading">
    <h2>News</h2>
  </div>
  <ol class="news-list">
    <li>
      <time>2026.05</time>
      <span>Launched this personal website.</span>
    </li>
    <li>
      <time>2026</time>
      <span>Working on research around large language models at UC Berkeley.</span>
    </li>
  </ol>
</section>

<section class="section">
  <div class="section-heading">
    <h2>Selected Writing</h2>
    <a href="{{ '/blog/' | relative_url }}">All posts</a>
  </div>
  <div class="writing-list">
    {% for post in site.posts limit:3 %}
      <article>
        <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%b %-d, %Y" }}</time>
        <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
        {% if post.excerpt %}
          <p>{{ post.excerpt | strip_html | truncate: 180 }}</p>
        {% endif %}
      </article>
    {% endfor %}
  </div>
</section>

<section class="section">
  <div class="section-heading">
    <h2>Publications</h2>
    <a href="{{ '/publications/' | relative_url }}">Full list</a>
  </div>
  <div class="publication-list">
    <article>
      <h3>Paper Title Goes Here</h3>
      <p><strong>Luke Lee</strong>, Collaborator Name, Advisor Name</p>
      <p>Conference or preprint, 2026. <a href="#">Paper</a> <a href="#">Code</a></p>
    </article>
  </div>
</section>
