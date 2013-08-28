<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:variable name="smallcase" select="'abcdefghijklmnopqrstuvwxyz-'" />
<xsl:variable name="uppercase" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ '" />

<xsl:template match="/">
      <section id="publications">
        <div class="page-header">
          <h1>Publications <small>papers</small></h1>
        </div>
        <xsl:for-each select="publi/article">
          <xsl:apply-templates select="." />
        </xsl:for-each>
      </section>
</xsl:template>

<xsl:template match="article">
        <div class="row">
          <div class="span3 columns">
            <h3><xsl:value-of select="year"/></h3>
            <p><xsl:element name="a">
                  <xsl:attribute name="href">
                    <xsl:value-of select="confsite"/>
                  </xsl:attribute><xsl:value-of select="conference"/></xsl:element></p>
          </div>
          <div class="span9 columns">
            <h3><xsl:value-of select="title"/></h3>
            <p><xsl:value-of select="abstract"/></p>
            <p><xsl:value-of select="authors"/></p>
            <div class="btn-group">
              <xsl:element name="a">
                <xsl:choose>
		  <xsl:when test="acm">
                    <xsl:attribute name="href"><xsl:value-of select="acm"/></xsl:attribute>
		  </xsl:when>
		  <xsl:otherwise>
                    <xsl:attribute name="href">/publications/<xsl:value-of select="translate(conference, $uppercase, $smallcase)"/>-<xsl:value-of select="year"/>.pdf</xsl:attribute>
		  </xsl:otherwise>
                </xsl:choose>
                <xsl:attribute name="class">btn btn-info<xsl:if test="published = 'no'"> disabled</xsl:if></xsl:attribute>PDF</xsl:element>
              <xsl:element name="a">
                <xsl:choose>
		  <xsl:when test="slides">
                    <xsl:attribute name="href"><xsl:value-of select="slides"/></xsl:attribute>
		  </xsl:when>
		  <xsl:otherwise>
                    <xsl:attribute name="href">/publications/<xsl:value-of select="translate(conference, $uppercase, $smallcase)"/>-<xsl:value-of select="year"/>-slides.pdf</xsl:attribute>
		  </xsl:otherwise>
                </xsl:choose>
                <xsl:attribute name="class">btn btn-info<xsl:if test="published = 'no'"> disabled</xsl:if></xsl:attribute>Slides</xsl:element>
              <xsl:element name="a">
                  <xsl:attribute name="href">/publications/<xsl:value-of select="translate(conference, $uppercase, $smallcase)"/>-<xsl:value-of select="year"/>.bib</xsl:attribute>
                  <xsl:attribute name="class">btn btn-info<xsl:if test="published = 'no'"> disabled</xsl:if></xsl:attribute>Bibtex</xsl:element>
            </div>
          </div>
        </div>
        <hr />
</xsl:template>

</xsl:stylesheet>
