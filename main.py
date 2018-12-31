class Tiddler(object):
  def __init__(self, attrs, data):
    self.attrs = attrs
    self.data = data
    self.name = self.get_name(attrs)
  
  def get_name(self, attrs):
    for k, v in attrs:
      if k == "tiddler":
        return v
  
  def __repr__(self):
    return "<%s, %s>" % (self.name, self.data)

class TiddlerImage(Tiddler):
  def __init__(self, *args):
    super(TiddlerImage, self).__init__(*args)
  
  def __repr__(self):
    return "<%s, %s>" % (self.name, "<image data>")

class TiddlerStylesheet(Tiddler):
  def __init__(self, attrs, data):
    super(TiddlerStylesheet, self).__init__(attrs, data)
    self.stylesheet_name = self.get_stylesheet_name(attrs)
    self.images = self.process_stylesheet_data(data)
  
  def get_stylesheet_name(self, attrs):
    for k, v in attrs:
      if k == "tags":
        if len(v.split(" ")) == 1:
          return ""
        else:
          return v.split(" ")[1]

  def process_stylesheet_data(self, data):
    img_names = []
    split_text = data.split("[")
    for i, text in enumerate(split_text[:-1]):
      if text == "img":
        if "]]" not in split_text[i+1]:
          print("BAD IMG EMBED", data)
        else:
          img_names.append(split_text[i+1].split("]]")[0])

    return img_names

  def __repr__(self):
    return "<%s, %s>" % (self.name, self.images)
  
  def is_stylesheet(attrs):
    #[True for k, v in attrs if (k =="tags" and v != "" and v.split(" ")[0] == "stylesheet")]
    for k, v in attrs:
      if k == "tags":
        if v != "" and v.split(" ")[0] == "stylesheet":
          return True
    return False

class TiddlerText(Tiddler):
  def __init__(self, attrs, data):
    super(TiddlerText, self).__init__(attrs, data)
    self.stylesheets = self.get_inherited_stylesheets(attrs)
    self.images = TiddlerStylesheet(attrs, data).process_stylesheet_data(data)
    self.text_split, self.effects = self.process_text_data(data)
    self.choices = self.get_choices_from_text_split(self.text_split)
    # print(self.text_split)
    # print(self.choices)
    # print(self.stylesheets)

  def get_inherited_stylesheets(self, attrs):
    for k, v in attrs:
      if k == "tags":
        return v.split(" ")

  def process_text_data(self, data):
    split_text = data.split("<<")
    unmerged_text = [((), split_text[0])]
    effects = []
    conditionals = []
    for text in split_text[1:]:
      if ">>" not in text:
        print("BAD DATA (hanging <<):", data)
      else:
        split_text_2 = text.split(">>")
        ifsplit = split_text_2[0].split(" ")
        
        if len(ifsplit) >= 2 and ifsplit[0] == "if":
          conditionals.append((" ".join(ifsplit[1:]), True))
        elif len(ifsplit) >= 2 and ifsplit[0] == "elseif":
          conditionals[-1] = (conditionals[-1][0], False)
          conditionals.append("elseif")
          conditionals.append((" ".join(ifsplit[1:]), True))
        elif split_text_2[0] == "else":
          conditionals[-1] = (conditionals[-1][0], False)
        elif split_text_2[0] == "endif":
          #print(conditionals)
          if len(conditionals) == 0:
            print(data)
          conditionals.pop()
          #print("post pop", conditionals)
          while conditionals and conditionals[-1] in ["elseif"]:
            conditionals.pop()
            conditionals.pop()
        else:
          #print(split_text_2)
          effects.append((self.cleaned_conditionals(conditionals), split_text_2[0]))
        unmerged_text.append((self.cleaned_conditionals(conditionals), split_text_2[1]))
    #print(unmerged_text)
    # print(effects)
    return tuple(unmerged_text), tuple(effects)

  def cleaned_conditionals(self, conditionals):
    res_list = []
    for conditional in conditionals:
      if conditional not in ["elseif"]:
        res_list.append(conditional)
    return tuple(res_list)

  def get_choices_from_text_split(self, text_split):
    choices = []
    for conditionals, text in text_split:
      if "[[" not in text:
        continue
      else:
        pre_split, text_split_2 = text.split("[[", 1)
        if "]]" not in text_split_2:
          print("BAD DATA (hanging [[):", text)
        else:
          choice_text_dest, text_split_3 = text_split_2.split("]]", 1)
          if "|" in choice_text_dest:
            choice_text, choice_dest_and_effects = choice_text_dest.split("|", 1)
            if "][" in choice_dest_and_effects:
              choice_dest_split = choice_dest_and_effects.split("][")
              choice_dest = choice_dest_split[0]
              choice_effects = choice_dest_split[1:]
            else:
              choice_dest = choice_dest_and_effects
              choice_effects = []
          else: #label is same as displayed text
            if "][" in choice_text_dest:
              choice_dest_split = choice_text_dest.split("][")
              choice_text = choice_dest_split[0]
              choice_dest = choice_dest_split[0]
              choice_effects = choice_dest_split[1:]
            else:
              choice_text = choice_text_dest
              choice_dest = choice_text_dest
              choice_effects = []
          choices.append((conditionals, (choice_text, choice_dest, choice_effects)))
          choices += self.get_choices_from_text_split(((conditionals, text_split_3),))
    return choices

from html.parser import HTMLParser

# assumes parse is given a list of divs in string form
class MyHTMLParser(HTMLParser):
  def __init__(self):
    super(MyHTMLParser, self).__init__()
    self.tiddler_divs = []
    self.reset_current_div()

  def reset_current_div(self):
    self.current_div_attrs = ()
    self.current_div_data = ''

  def handle_starttag(self, tag, attrs):
    # print("Encountered a start tag:", tag, attrs)
    self.current_div_attrs = attrs

  def handle_endtag(self, tag):
    #print("Encountered an end tag :", tag)
    if [True for k, v in self.current_div_attrs if k == "tiddler"]:
      self.tiddler_divs.append((self.current_div_attrs,
                                self.current_div_data))
    else:
      #print("have some problems recording data", self.current_div_attrs, self.current_div_data)
      pass
    self.reset_current_div()    

  def handle_data(self, data):
    #print("Encountered some data  :", data)
    self.current_div_data = data
  
  def postprocess_tiddler(self):
    res = {}
    for attrs, data in self.tiddler_divs:
      if [True for k, v in attrs if (k, v) == ("tags", "Twine.image")]:
        tiddler = TiddlerImage(attrs, data)
      elif TiddlerStylesheet.is_stylesheet(attrs):
        tiddler = TiddlerStylesheet(attrs, data)
      else:
        tiddler = TiddlerText(attrs, data)
      if tiddler.name in res:
        print("ERROR (duplicate tiddler):", tiddler.name)
      res[tiddler.name] = tiddler

    return res

def graphify_tiddlers(tiddlers):
  stylesheet_lookup = {}
  for name, tiddler in tiddlers.items():
    if type(tiddler) == TiddlerStylesheet:
      stylesheet_lookup[tiddler.stylesheet_name] = tiddler.name
  print(stylesheet_lookup)
  for name, tiddler in tiddlers.items():
    tiddler.indegrees = []
    tiddler.outdegrees = []
  for name, tiddler in tiddlers.items():
    if type(tiddler) == TiddlerImage:
      continue
    if type(tiddler) in [TiddlerStylesheet, TiddlerText]:
      for image in tiddler.images:
        if image not in tiddlers:
          print("WARNING (image referenced but not found):", image)
        else:
          tiddler.outdegrees.append(image)
    if type(tiddler) == TiddlerText:
      for stylesheet in tiddler.stylesheets:
        if stylesheet not in ["bookmark", "script"]: #protected twine tags
          if stylesheet not in stylesheet_lookup:
            print("WARNING (broken, useless and/or unregistered tag):", stylesheet)
          else:
            tiddler.outdegrees.append(stylesheet_lookup[stylesheet])
      for cond, choice_tuple in tiddler.choices:
        text, dest, effects = choice_tuple
        if dest not in ["previous()"]:
          if dest not in tiddlers:
            print("WARNING (choice destination not found):", dest)
          else:
            tiddler.outdegrees.append(dest)
      for conds, effect in tiddler.effects:
        if effect.startswith("display "):
          dest = effect.split(" ", 1)[1]
          if dest not in tiddlers:
            print("WARNING (display destination not found):", dest)
          else:
            tiddler.outdegrees.append(dest)
  for name, tiddler in tiddlers.items():
    for outdegree in tiddler.outdegrees:
      tiddlers[outdegree].indegrees.append(name)
  for name, tiddler in tiddlers.items():
    if tiddler.indegrees == []:
      print(name)

def tiddlers_graph_order(tiddlers):
  # Idea: the graph is converted into a tree (where any loops are removed)
  # For each origin (a tiddler with no indegrees), the tiddler is iterated through in a depth-first fashion.
  # There's multiple branches, which have starts and ends, and may even merge to later points.
  # These branches are merged.
  # A B C1 C2 D
  # In this case, the order of evaluation is A B D (C1 C2), and since C1 C2 is bigger than B, it is placed between B and D (otherwise placed between A and B)
  # This is not guaranteed to work with all trees.
  # If outdegree is a stylesheet or image, always include the referenced image
  ordered_tiddlers = []
  for name, tiddler in tiddler.items():
    if tiddler.indegrees == []:
      res = [(None,name), name]
      for outdegree in tiddler.outdegrees:
        l = generate_list(tiddlers[outdegree], current_list, master_list)
        res = merge_list(res, l, ordered_tiddlers)

  for name, tiddler in tiddler.items():
    if tiddler.indegrees == []:
      res = generate_list(tiddler, ordered_tiddlers)
      ordered_tiddlers = merge_list(res, ordered_tiddlers)


def generate_list(tiddler, master_list, current_list = []):
  pass #TODO

def merge_list(cumulative_res, temp_res):
  if res[-1] in ordered_res:
    if res[1] in ordered_res:
      ordered_res = ordered_res[:-1] + res + ordered_res[-1:]

def find_merge_point(res1, res2):
  if res1[-1][0] not in res2 and res1[0][1] not in res1:
    get_branch_lengths(res1[-1][0], res1[0][1], len(res1))


    #dead end, so must be inserted at very beginning, very end, or at one of the starts of the branch.

def find_merge_point_2(res1, res2):
  looking_for_start = True
  start_index = 0
  current_best_index = 0
  for i, v in enumerate(res2):
    if looking_for_start: # avoid resetting index on sub-forks.
      if type(v) == tuple and v[0] == res1[0][0]:
        start_index = i
        looking_for_start = False
    else:
      if type(v) == tuple and v[1] == res1[-1][1]:
        segment_length = 1+i-start_index
        if segment_length > len_reference:
          return start_index
        else:
          current_best_index = i+1
          looking_for_start = True
  return current_best_index

# A B1 B2 C1 C2 D E
# insert A F G E

def get_branch_lengths(res2, start, stop, len_reference):
  start_index = 0
  current_best_index = 0
  for i, v in enumerate(res2):
    if type(v) == tuple and v[0] == start:
      start_index = i
    if type(v) == tuple and v[1] == stop:
      segment_length = i-start_index
      if segment_length > len_reference:
        return start_index
      else:
        current_best_index = i+1
  return current_best_index


import sys
# instantiate the parser and fed it some HTML
parser = MyHTMLParser()
with open(sys.argv[1]) as f:
  for line in f.readlines():
    if "tiddler=" in line:
      parser.feed(line)
tiddlers = parser.postprocess_tiddler()
graphify_tiddlers(tiddlers)