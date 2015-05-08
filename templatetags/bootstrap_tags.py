from django import template
from django.template.loader import render_to_string

register = template.Library()

class AccordionGroupNode(template.Node):
    '''Implements a bootstrap accordion panel-group'''
    def __init__(self, groupid, nodelist):
        self.groupid, self.nodelist = groupid, nodelist

    def render(self, context):
        with context.push():
            context['groupid'] = self.groupid
            return ('<div class="panel-group" id="#{}">'.format(self.groupid)
                    + self.nodelist.render(context)
                    + '</div>')


@register.tag
def accordiongroup(parser, token):
    '''Bootstrap accordion panel-group'''
    args = token.split_contents()
    if len(args) != 2:
        raise template.TemplateSyntaxError(
            "'accordiongroup' tag requires exactly one argument.")
    groupid = args[1]
    nodelist = parser.parse(('endaccordiongroup',))
    parser.delete_first_token()
    return AccordionGroupNode(groupid, nodelist)


class AccordionPanelNode(template.Node):
    '''Implements a single accordion panel for bootstrap'''
    def __init__(self, panelid, panel_title, in_opt, nodelist):
        self.panelid = panelid
        self.panel_title = panel_title
        self.in_opt = in_opt
        self.nodelist = nodelist

    def render(self, context):
        in_opt = context.get(self.in_opt) or self.in_opt.lower() == 'in'
        inner_context = dict(panelid=self.panelid,
                             panel_title=self.panel_title,
                             in_opt=in_opt)
        return (render_to_string('bootstrap/accordion_panel_begin.html',
                                 inner_context) +
                self.nodelist.render(context) + 
                render_to_string('bootstrap/accordion_panel_end.html',
                                 inner_context))


@register.tag
def accordionpanel(parser, token):
    '''Bootstrap accordion panel-group'''
    args = token.split_contents()
    if not 3 <= len(args) <= 4:
        raise template.TemplateSyntaxError(
            "'accordiongroup' tag requires 3 or 4 arguments.")
    panelid = args[1]
    panel_title = args[2]
    in_opt = args[3] if len(args) == 4 else ''
    nodelist = parser.parse(('endaccordionpanel',))
    parser.delete_first_token()
    return AccordionPanelNode(panelid, panel_title, in_opt, nodelist)
