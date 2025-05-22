<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
  xmlns:se="http://www.opengis.net/se"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:sld="http://www.opengis.net/sld"
  exclude-result-prefixes="sld se">

  <xsl:output encoding="UTF-8"/>

  <!--
    Chanage the version and the schemaLocation values
  -->

  <xsl:template match="/sld:StyledLayerDescriptor">
    <StyledLayerDescriptor xmlns="http://www.opengis.net/sld"
       xmlns:ogc="http://www.opengis.net/ogc"
       xmlns:xlink="http://www.w3.org/1999/xlink"
       xmlns:gml="http://www.opengis.net/gml">
      <xsl:apply-templates select="@*"/>
      <xsl:attribute name="version">1.0.0</xsl:attribute>
      <xsl:attribute name="xsi:schemaLocation"
        namespace="http://www.w3.org/2001/XMLSchema-instance">
        <xsl:text>http://www.opengis.net/sld </xsl:text>
        <xsl:text>http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd</xsl:text>
      </xsl:attribute>
      <xsl:apply-templates/>
    </StyledLayerDescriptor>
  </xsl:template>

  <!--
    Map SvgParameter elements in the http://www.opengis.net/se namespace
    to CssParameter in the http://www.opengis.net/sld namespace
  -->

  <xsl:template match="se:SvgParameter">
    <xsl:element name="CssParameter" namespace="http://www.opengis.net/sld">
      <xsl:apply-templates select="@*"/>
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>

  <!--
    Map remaining http://www.opengis.net/se elements and attributes
    to the http://www.opengis.net/sld namespace
  -->

  <xsl:template match="se:*">
    <xsl:element name="{local-name()}" namespace="http://www.opengis.net/sld">
      <xsl:apply-templates select="@*"/>
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>

  <!--
   Preserve all other elements and attributes
  -->

  <xsl:template match="*|@*">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

  <!--
   Preserve processing instructuions and comments
  -->

  <xsl:template match="processing-instruction()|comment()">
    <xsl:copy>.</xsl:copy>
  </xsl:template>

</xsl:stylesheet>
