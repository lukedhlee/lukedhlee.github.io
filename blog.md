---
layout: default
title: Blog
permalink: /blog/
---

<section class="page-title">
  <h1>Blog</h1>
  <p>Notes on LLMs, research ideas, papers, and engineering details.</p>
</section>

<section class="section">
  <div class="writing-list writing-list-large">
    {% for post in site.posts %}
      <article>
        <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%B %-d, %Y" }}</time>
        <h2><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h2>
        <p>{{ post.excerpt | strip_html | truncate: 240 }}</p>
      </article>
    {% endfor %}
  </div>
</section>
